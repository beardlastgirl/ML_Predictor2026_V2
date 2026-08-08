# Model creation and prediction

import numpy as np
import pandas as pd
from scipy.stats import poisson as _poisson
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from src.config import (
    MODEL_PARAMS, BASE_ELO, TRAILING_WINDOW,
    WIN_PROBABILITY_THRESHOLD, DRAW_PROBABILITY_THRESHOLD,
    DEFAULT_EXPECTED_GOALS, MAX_PREDICTED_GOALS, ML_POISSON_BLEND_RATIO
)
from src.utils import log_info
from src.stats_engine import calculate_poisson_features
from src.features import get_all_teams_latest_stats
from src.cold_start import extract_shin_probabilities, calculate_bayesian_shrunk_xg

# Alias for backward-compat within this module
MAX_GOALS = MAX_PREDICTED_GOALS

def create_model(model_type, class_weights=None):
    """Create a fresh model instance with configured hyperparameters.

    Args:
        model_type: Type of model ('lightgbm' or 'catboost')
        class_weights: Optional dict of class weights for imbalanced data
    """
    params = MODEL_PARAMS[model_type].copy() if model_type in MODEL_PARAMS else {}

    if class_weights:
        if model_type == "catboost":
            params["class_weights"] = [class_weights.get(i, 1.0) for i in range(3)]
        elif model_type == "lightgbm":
            params["class_weight"] = class_weights

    if model_type == "lightgbm":
        return LGBMClassifier(**params)
    elif model_type == "catboost":
        return CatBoostClassifier(**params)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

def _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a):
    """
    Calculate realistic scorelines using the Poisson distribution's most-likely
    scoreline, adjusted by the ML outcome prediction.

    Uses the mode of the Poisson distribution (most probable integer) rather than
    rounding the mean, which avoids collapsing all xG values in [0.5, 1.5] to 1.
    """
    # Most likely goals = mode of Poisson = floor(xG) for xG >= 1, else 0
    # This gives more spread than round() for low-xG matches
    m_h = int(np.floor(max(0.0, exp_h)))
    m_a = int(np.floor(max(0.0, exp_a)))

    # ML adjustment: apply when the model has a clear directional prediction.
    # Threshold is on the raw probability, not a scaled weight.
    max_prob = max(p_h, p_d, p_a)

    if max_prob >= 0.35:  # model has some confidence
        if ml_pred == 2 and p_h >= p_d and p_h >= p_a:  # home win predicted
            # Ensure home > away; if already so, optionally bump by 1 for strong predictions
            if m_h <= m_a:
                m_h = m_a + 1
            elif p_h >= 0.50:  # strong home win — add a goal
                m_h = min(MAX_GOALS, m_h + 1)
        elif ml_pred == 0 and p_a >= p_h and p_a >= p_d:  # away win predicted
            if m_a <= m_h:
                m_a = m_h + 1
            elif p_a >= 0.50:
                m_a = min(MAX_GOALS, m_a + 1)
        elif ml_pred == 1 and p_d >= p_h and p_d >= p_a:  # draw predicted
            # Equalise scores at the higher of the two floor values
            score = max(m_h, m_a)
            m_h = m_a = score

    return max(0, min(MAX_GOALS, m_h)), max(0, min(MAX_GOALS, m_a))

def predict_gameweek(fixtures_df, elo_ratings, model, features, df_mean=None, historical_matches=None, sofascore_data=None):
    """Generate predictions with Poisson-enhanced modeling."""
    if fixtures_df.empty:
        return fixtures_df
    fixtures_df = fixtures_df.copy()
    
    # Precompute team stats once
    latest_stats = {}
    if historical_matches is not None:
        latest_stats = get_all_teams_latest_stats(historical_matches, TRAILING_WINDOW)

    if sofascore_data:
        for side in ["Home", "Away"]:
            fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[f"{side}Team"].apply(lambda x: sofascore_data.get(str(x).upper(), {}).get("position", 28))
            fixtures_df[f"{side}_Sofa_Points"] = fixtures_df[f"{side}Team"].apply(lambda x: sofascore_data.get(str(x).upper(), {}).get("points", 0))
            fixtures_df[f"{side}_Sofa_GF"] = fixtures_df[f"{side}Team"].apply(lambda x: sofascore_data.get(str(x).upper(), {}).get("goals_for", 0))
            fixtures_df[f"{side}_Sofa_GA"] = fixtures_df[f"{side}Team"].apply(lambda x: sofascore_data.get(str(x).upper(), {}).get("goals_against", 0))
    
    # Map Elo and features in a more vectorized way if possible
    fixtures_df["Home_Elo"] = fixtures_df["HomeTeam"].map(elo_ratings).fillna(BASE_ELO)
    fixtures_df["Away_Elo"] = fixtures_df["AwayTeam"].map(elo_ratings).fillna(BASE_ELO)
    
    # Build team stats efficiently
    stats_cols = ["Avg_GF", "Avg_GA", "Form"]
    for side in ["Home", "Away"]:
        for col in stats_cols:
            full_col = f"{side}_{col}"
            default_val = df_mean.get(full_col, 1.0 if "Avg" in col else 0.5) if df_mean else (1.0 if "Avg" in col else 0.5)
            key = col.lower().replace("avg_", "")
            fixtures_df[full_col] = fixtures_df[f"{side}Team"].apply(lambda x: latest_stats.get(x, {}).get(key, default_val))

    # Vectorized Poisson calculation (requires stats_engine refactor but let's do it row-wise for now and optimize later if needed)
    poisson_features = fixtures_df.apply(
        lambda r: calculate_poisson_features(
            r["Home_Elo"], r["Away_Elo"], r["Home_Avg_GF"], r["Away_Avg_GF"], r["Home_Avg_GA"], r["Away_Avg_GA"]
        ), axis=1
    )
    poisson_df = pd.DataFrame(list(poisson_features), index=fixtures_df.index)
    fixtures_df = pd.concat([fixtures_df, poisson_df], axis=1)
    
    fixtures_df["Elo_Diff"] = fixtures_df["Home_Elo"] - fixtures_df["Away_Elo"]
    fixtures_df["Attack_Balance"] = fixtures_df["Home_Avg_GF"] - fixtures_df["Away_Avg_GF"]
    fixtures_df["Def_Balance"] = fixtures_df["Away_Avg_GA"] - fixtures_df["Home_Avg_GA"]
    fixtures_df["Form_Balance"] = fixtures_df["Home_Form"] - fixtures_df["Away_Form"]

    # --- Shin probabilities from odds (if available) ---
    odds_cols_map = {
        "h": ["Odds_b365_H", "B365CH"],
        "d": ["Odds_b365_D", "B365CD"],
        "a": ["Odds_b365_A", "B365CA"],
    }

    def _get_odds_col(fixtures_df, candidates):
        for c in candidates:
            if c in fixtures_df.columns:
                return c
        return None

    col_h = _get_odds_col(fixtures_df, odds_cols_map["h"])
    col_d = _get_odds_col(fixtures_df, odds_cols_map["d"])
    col_a = _get_odds_col(fixtures_df, odds_cols_map["a"])

    if col_h and col_d and col_a:
        def _shin_row(r):
            try:
                odds_h, odds_d, odds_a = float(r[col_h]), float(r[col_d]), float(r[col_a])
                if any(v <= 0 or np.isnan(v) for v in [odds_h, odds_d, odds_a]):
                    return np.nan, np.nan, np.nan
                probs = extract_shin_probabilities(odds_h, odds_d, odds_a)
                return probs[0], probs[1], probs[2]
            except Exception:
                return np.nan, np.nan, np.nan

        shin_results = fixtures_df.apply(_shin_row, axis=1)
        fixtures_df["Shin_Prob_H"] = [r[0] for r in shin_results]
        fixtures_df["Shin_Prob_D"] = [r[1] for r in shin_results]
        fixtures_df["Shin_Prob_A"] = [r[2] for r in shin_results]
    else:
        # No odds available; fill will happen in the feature-fill loop below
        fixtures_df["Shin_Prob_H"] = np.nan
        fixtures_df["Shin_Prob_D"] = np.nan
        fixtures_df["Shin_Prob_A"] = np.nan

    # --- Bayesian-shrunk xG meta-features ---
    # For live fixtures we don't know the exact matchday; use 1 as conservative default
    # (maximum shrinkage toward league mean — safe for cold-start).
    fixtures_df["poisson_xg_home_meta"] = fixtures_df.apply(
        lambda r: calculate_bayesian_shrunk_xg(
            r.get("xG_home", np.nan) if not np.isnan(r.get("xG_home", np.nan)) else (df_mean.get("xG_home", 1.15) if df_mean else 1.15),
            matchday=1,
        ),
        axis=1,
    )
    fixtures_df["poisson_xg_away_meta"] = fixtures_df.apply(
        lambda r: calculate_bayesian_shrunk_xg(
            r.get("xG_away", np.nan) if not np.isnan(r.get("xG_away", np.nan)) else (df_mean.get("xG_away", 1.15) if df_mean else 1.15),
            matchday=1,
        ),
        axis=1,
    )

    for col in features:
        if col not in fixtures_df.columns: 
            fixtures_df[col] = df_mean.get(col, 0) if df_mean else 0
        fixtures_df[col] = fixtures_df[col].fillna(df_mean.get(col, 0) if df_mean else 0)
    
    # ML Model Prediction — pure model output (Poisson feeds GBM as features, no post-hoc blend)
    proba = model.predict_proba(fixtures_df[features])

    fixtures_df["Prediction"] = np.argmax(proba, axis=1)
    fixtures_df["Pred_Proba_Home"] = proba[:, 2]
    fixtures_df["Pred_Proba_Draw"] = proba[:, 1]
    fixtures_df["Pred_Proba_Away"] = proba[:, 0]

    # Apply hybrid goal prediction
    results = fixtures_df.apply(
        lambda r: _calculate_hybrid_goals(
            r.get("Expected_Home_Goals", DEFAULT_EXPECTED_GOALS),
            r.get("Expected_Away_Goals", DEFAULT_EXPECTED_GOALS),
            int(r["Prediction"]),
            r["Pred_Proba_Home"], r["Pred_Proba_Draw"], r["Pred_Proba_Away"]
        ), axis=1
    )
    
    fixtures_df["Pred_Home_Goals"] = [r[0] for r in results]
    fixtures_df["Pred_Away_Goals"] = [r[1] for r in results]
    
    fixtures_df["Prediction_Label"] = fixtures_df.apply(
        lambda r: "Home Win" if r["Pred_Home_Goals"] > r["Pred_Away_Goals"] 
        else ("Away Win" if r["Pred_Home_Goals"] < r["Pred_Away_Goals"] else "Draw"), axis=1
    )
    return fixtures_df
