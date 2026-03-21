# Model creation and prediction

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from src.config import (
    MODEL_PARAMS, BASE_ELO, TRAILING_WINDOW,
    WIN_PROBABILITY_THRESHOLD, DRAW_PROBABILITY_THRESHOLD,
    DEFAULT_EXPECTED_GOALS, MAX_PREDICTED_GOALS
)
from src.utils import log_info
from src.stats_engine import calculate_poisson_features
from src.features import get_all_teams_latest_stats

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

def predict_gameweek(fixtures_df, elo_ratings, model, features, df_mean=None, historical_matches=None, sofascore_data=None):
    """Generate predictions with Poisson-enhanced modeling."""
    if fixtures_df.empty:
        return fixtures_df
    fixtures_df = fixtures_df.copy()
    
    # Precompute team stats once if historical_matches provided
    latest_stats = {}
    if historical_matches is not None:
        latest_stats = get_all_teams_latest_stats(historical_matches, TRAILING_WINDOW)
        log_info(f"Precomputed trailing stats for {len(latest_stats)} teams")

    if sofascore_data:
        for side in ["Home", "Away"]:
            def get_sofa_value(team_name, key, default=None):
                """Safely get Sofascore data with fallback."""
                try:
                    if isinstance(team_name, str):
                        return sofascore_data.get(team_name.upper(), {}).get(key, default)
                    return default
                except (AttributeError, TypeError):
                    return default
            
            fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[side].apply(lambda x: get_sofa_value(x, "position", 28))
            fixtures_df[f"{side}_Sofa_Points"] = fixtures_df[side].apply(lambda x: get_sofa_value(x, "points", 0))
            fixtures_df[f"{side}_Sofa_GF"] = fixtures_df[side].apply(lambda x: get_sofa_value(x, "goals_for", 0))
            fixtures_df[f"{side}_Sofa_GA"] = fixtures_df[side].apply(lambda x: get_sofa_value(x, "goals_against", 0))
        log_info(f"Added Sofascore features for {len(sofascore_data)} teams")
    
    for side in ["Home", "Away"]:
        fixtures_df[f"{side}_Elo"] = fixtures_df[side].map(elo_ratings).fillna(BASE_ELO)
    
    team_stats_list = []
    for _, row in fixtures_df.iterrows():
        h_stats = latest_stats.get(row["Home"], {})
        a_stats = latest_stats.get(row["Away"], {})
        
        team_stats_list.append({
            "Home_Avg_GF": h_stats.get("avg_gf", df_mean.get("Home_Avg_GF", 1.0) if df_mean else 1.0),
            "Home_Avg_GA": h_stats.get("avg_ga", df_mean.get("Home_Avg_GA", 1.0) if df_mean else 1.0),
            "Home_Form": h_stats.get("form", df_mean.get("Home_Form", 0.5) if df_mean else 0.5),
            "Away_Avg_GF": a_stats.get("avg_gf", df_mean.get("Away_Avg_GF", 1.0) if df_mean else 1.0),
            "Away_Avg_GA": a_stats.get("avg_ga", df_mean.get("Away_Avg_GA", 1.0) if df_mean else 1.0),
            "Away_Form": a_stats.get("form", df_mean.get("Away_Form", 0.5) if df_mean else 0.5),
        })
    fixtures_df = pd.concat([fixtures_df, pd.DataFrame(team_stats_list, index=fixtures_df.index).reset_index(drop=True)], axis=1)
    
    poisson_features = []
    for _, row in fixtures_df.iterrows():
        pf = calculate_poisson_features(
            row["Home_Elo"], row["Away_Elo"], 
            row["Home_Avg_GF"], row["Away_Avg_GF"], 
            row["Home_Avg_GA"], row["Away_Avg_GA"]
        )
        poisson_features.append(pf)
    fixtures_df = pd.concat([fixtures_df, pd.DataFrame(poisson_features, index=fixtures_df.index)], axis=1)
    
    fixtures_df["Elo_Diff"] = fixtures_df["Home_Elo"] - fixtures_df["Away_Elo"]
    fixtures_df["Attack_Balance"] = fixtures_df["Home_Avg_GF"] - fixtures_df["Away_Avg_GF"]
    fixtures_df["Def_Balance"] = fixtures_df["Away_Avg_GA"] - fixtures_df["Home_Avg_GA"]
    fixtures_df["Form_Balance"] = fixtures_df["Home_Form"] - fixtures_df["Away_Form"]
    
    for col in features:
        if col not in fixtures_df.columns: 
            fixtures_df[col] = df_mean.get(col, 0) if df_mean else 0
        fixtures_df[col] = fixtures_df[col].fillna(df_mean.get(col, 0) if df_mean else 0)
    
    # ML Model Prediction with Poisson ensemble
    # Combine ML probabilities with Poisson-derived probabilities for better calibration
    proba = model.predict_proba(fixtures_df[features])

    # Hybrid prediction: blend ML probabilities with Poisson probabilities
    # This helps reduce draw bias by incorporating Poisson-derived outcomes
    poisson_home = fixtures_df["Poisson_Home_Win"].values
    poisson_draw = fixtures_df["Poisson_Draw"].values
    poisson_away = fixtures_df["Poisson_Away_Win"].values

    # Ensemble: 60% ML, 40% Poisson (Poisson is better calibrated for outcomes)
    ensemble_alpha = 0.6
    blended_proba = np.zeros_like(proba)
    blended_proba[:, 0] = ensemble_alpha * proba[:, 0] + (1 - ensemble_alpha) * poisson_away
    blended_proba[:, 1] = ensemble_alpha * proba[:, 1] + (1 - ensemble_alpha) * poisson_draw
    blended_proba[:, 2] = ensemble_alpha * proba[:, 2] + (1 - ensemble_alpha) * poisson_home

    # Use blended probabilities for prediction
    fixtures_df["Prediction"] = np.argmax(blended_proba, axis=1)
    fixtures_df["Pred_Proba_Home"] = blended_proba[:, 2]
    fixtures_df["Pred_Proba_Draw"] = blended_proba[:, 1]
    fixtures_df["Pred_Proba_Away"] = blended_proba[:, 0]

    # Goal Prediction Logic
    pred_home_goals, pred_away_goals = [], []
    for i in range(len(fixtures_df)):
        row = fixtures_df.iloc[i]
        exp_h = row.get("Expected_Home_Goals", DEFAULT_EXPECTED_GOALS)
        exp_a = row.get("Expected_Away_Goals", DEFAULT_EXPECTED_GOALS)
        ml_pred = int(row["Prediction"])
        # Use blended probabilities
        p_a = row["Pred_Proba_Away"]
        p_d = row["Pred_Proba_Draw"]
        p_h = row["Pred_Proba_Home"]

        # Start with rounded expected goals
        m_h, m_a = int(round(exp_h)), int(round(exp_a))

        # Adjust based on prediction confidence with higher thresholds
        # Only predict draw when Poisson and ML both strongly suggest it

        # Special case: Away win when away team has significantly higher xG
        # This overrides ML prediction to ensure we get some away wins
        xG_diff = exp_a - exp_h  # Positive means away team has higher xG

        # More aggressive away win detection
        # If away team has notably higher xG, favor away win
        if xG_diff > 0.20:
            # Away team clearly better - predict away win
            ml_pred = 0
            if m_a <= m_h: m_a = m_h + 1
        elif xG_diff > 0.10 and p_a > p_d:
            # Moderate xG advantage and away win more likely than draw
            ml_pred = 0
            if m_a <= m_h: m_a = m_h + 1
        elif ml_pred == 2 and p_h >= WIN_PROBABILITY_THRESHOLD:  # Home Win
            if m_h <= m_a: m_h = m_a + 1
        elif ml_pred == 0 and p_a >= WIN_PROBABILITY_THRESHOLD:  # Away Win (ML predicted)
            if m_a <= m_h: m_a = m_h + 1
        elif ml_pred == 1 and p_d >= DRAW_PROBABILITY_THRESHOLD:  # Draw
            # For draws, use xG to determine realistic scoreline variance
            # League draws occur at: 0-0 (~8%), 1-1 (~15%), 2-2 (~5%), etc.
            total_xg = exp_h + exp_a

            if total_xg < 1.0:
                # Low-scoring draw: 0-0 or 1-1 based on xG
                m_h = m_a = 0 if total_xg < 0.6 else 1
            elif total_xg < 2.5:
                # Medium-scoring draw: mostly 1-1, some 2-1/1-2 feel
                m_h = m_a = 1
            elif total_xg < 3.5:
                # Higher-scoring draw: 2-2 or 2-1
                m_h = m_a = 2
            else:
                # High-scoring: 2-2 or 3-3
                m_h = m_a = min(3, max(2, round(total_xg / 2)))

            # Add subtle xG-based adjustment: if xG differs significantly,
            # nudge the scoreline slightly while keeping draw outcome
            xG_diff_internal = exp_h - exp_a
            if abs(xG_diff_internal) > 0.4:
                # Strong team "deserves" more but it's a draw - show in score
                if xG_diff_internal > 0.4 and m_h >= 1:
                    m_h = min(m_h + 1, MAX_PREDICTED_GOALS)  # e.g., 2-1 becomes possible
                    m_a = max(1, m_a)
                elif xG_diff_internal < -0.4 and m_a >= 1:
                    m_a = min(m_a + 1, MAX_PREDICTED_GOALS)
                    m_h = max(1, m_h)

        pred_home_goals.append(max(0, min(MAX_PREDICTED_GOALS, m_h)))
        pred_away_goals.append(max(0, min(MAX_PREDICTED_GOALS, m_a)))
        
    fixtures_df["Pred_Home_Goals"], fixtures_df["Pred_Away_Goals"] = pred_home_goals, pred_away_goals
    fixtures_df["Prediction_Label"] = fixtures_df.apply(
        lambda r: "Home Win" if r["Pred_Home_Goals"] > r["Pred_Away_Goals"] 
        else ("Away Win" if r["Pred_Home_Goals"] < r["Pred_Away_Goals"] else "Draw"), axis=1
    )
    return fixtures_df
