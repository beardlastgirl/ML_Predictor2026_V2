"""
ML_Predictor2026_V2 - Prediction Pipeline Service

Application service that orchestrates the prediction workflow:
- load_data: Load and normalize historical data
- build_features: Compute Elo, trailing stats, and Poisson features
- train_validate: Train model with time-series cross-validation
- predict_fixtures: Generate predictions for upcoming matches
- write_outputs: Save results and generate reports
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
# from sklearn.model_selection import TimeSeriesSplit  # Replaced by tournament-aware CV
from src.cv_split import make_tournament_aware_cv, TournamentAwareTimeSeriesSplit

from src.config import (
    BASE_ELO, MODEL_TYPE, TRAILING_WINDOW, RESULT_ENCODING,
    CONFIDENCE_STRONG_THRESHOLD, CONFIDENCE_MODERATE_THRESHOLD,
    BASE_GOAL_RATE,
)
from src.utils import log_info, log_ok, log_error, log_warning
from src.data_processing import (
    load_glossary, load_sofascore_data, normalize_team_name,
    clean_partidos_file, parse_fixtures
)
from src.stats_engine import (
    calculate_poisson_features,
    shin_method,
)
from src.batched_features import (
    calculate_all_elo_ratings_batched,
    compute_trailing_features_batched,
    prepare_temporal_batches,
)
from src.model_engine import create_model, predict_gameweek
from src.validation import validate_pipeline_inputs, validate_model_features

matplotlib.use("Agg")

FEATURE_COLUMNS = [
    "Home_Elo", "Away_Elo", "Elo_Diff",
    "Home_Avg_GF", "Away_Avg_GF", "Home_Avg_GA", "Away_Avg_GA",
    "Home_Form", "Away_Form",
    "Attack_Balance", "Def_Balance", "Form_Balance",
    "xG_home", "xG_away", "xG_diff",
    "Poisson_Home_Win", "Poisson_Draw", "Poisson_Away_Win",
    "Expected_Home_Goals", "Expected_Away_Goals", "Expected_Total_Goals",
    "Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A",
]


class PipelineResult:
    """Container for pipeline execution results."""

    def __init__(self):
        self.model = None
        self.elo_ratings: Dict = {}
        self.features: List[str] = []
        self.cv_accuracies: List[float] = []
        self.cv_log_losses: List[float] = []
        self.fixtures: Optional[pd.DataFrame] = None
        self.output_file: Optional[str] = None
        self.feature_importance: Optional[pd.DataFrame] = None


def load_data(
    glossary_path: str = "Glossary.txt",
    sofascore_path: str = "src/sofascore_stats.json",
    fixtures_path: str = "partidos.txt",
    historical_path: str = "data/ARG.csv"
) -> Tuple[Dict, Dict, pd.DataFrame, Optional[pd.DataFrame]]:
    """Load and normalize all input data.

    Args:
        glossary_path: Path to team name glossary
        sofascore_path: Path to Sofascore standings JSON
        fixtures_path: Path to fixtures file
        historical_path: Path to historical match data CSV

    Returns:
        Tuple of (glossary, sofascore_data, matches_df, fixtures_df)
    """
    log_info("Loading data...")

    glossary = load_glossary(glossary_path)
    sofascore_data = load_sofascore_data(sofascore_path)

    if os.path.exists(fixtures_path):
        clean_partidos_file(fixtures_path, glossary)
    else:
        log_warning(f"Fixtures file not found: {fixtures_path}")

    try:
        matches = pd.read_csv(historical_path)
        
        # Validate required columns exist
        required_cols = ["Home", "Away", "Res", "Date"]
        missing_cols = [col for col in required_cols if col not in matches.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        matches = matches.dropna(subset=["Home", "Away", "Res"])
        matches["Date"] = pd.to_datetime(matches["Date"], dayfirst=True, errors="coerce")
        matches = matches.dropna(subset=["Date"])
        matches["Time"] = matches["Time"].where(matches["Time"].notna(), "").astype(str).str.strip()
        matches["Home"] = matches["Home"].map(lambda x: normalize_team_name(x, glossary))
        matches["Away"] = matches["Away"].map(lambda x: normalize_team_name(x, glossary))
        matches["Res"] = matches["Res"].map(RESULT_ENCODING)
        
        # Validate result encoding - warn if any unmapped results
        if matches["Res"].isna().any():
            unmapped_count = matches["Res"].isna().sum()
            log_warning(f"{unmapped_count} matches have invalid result codes (not H/D/A)")
        
        # Unknown and 00:xx kickoffs are conservatively batched by date.
        matches = prepare_temporal_batches(matches).drop(
            columns=["_temporal_batch", "_temporal_order", "_temporal_row_id"]
        )
        log_ok(f"Historical matches loaded: {len(matches)}")
    except Exception as e:
        log_error(f"Error reading historical data: {e}")
        raise

    fixtures, _fixtures_header, _fixtures_summary = parse_fixtures(fixtures_path, glossary)
    
    # Run validation checks
    is_valid, errors = validate_pipeline_inputs(glossary, matches, fixtures, sofascore_data)
    if not is_valid:
        log_warning("Data validation completed with warnings/errors (see above)")
    
    return glossary, sofascore_data, matches, fixtures


def build_features(matches: pd.DataFrame, form_variant: Optional[Dict] = None) -> Tuple[pd.DataFrame, Dict]:
    """Compute all features for model training.

    Args:
        matches: DataFrame with normalized match data
        form_variant: None (baseline) or a sporting-form variant spec forwarded
            to compute_trailing_features_batched (experiment harness only;
            production callers use None). See batched_features for the spec.

    Returns:
        Tuple of (feature_dataframe, elo_ratings_dict)
    """
    log_info("Building features...")

    # A single normalized order drives Elo, trailing form, Poisson, CV, and labels.
    matches = prepare_temporal_batches(matches)

    # --- Start: Shin Method Integration ---
    log_info("Calculating Shin Method probabilities from odds...")

    def calculate_shin_probs(row):
        """Helper to apply shin_method to a row."""
        odds_cols = ["B365CH", "B365CD", "B365CA"]
        if not all(c in row and pd.notna(row[c]) for c in odds_cols):
            # Impute neutral probabilities for missing odds (1/3 each)
            # This prevents dropna from discarding 90%+ of training data
            return [1.0/3.0, 1.0/3.0, 1.0/3.0]

        odds = [row["B365CH"], row["B365CD"], row["B365CA"]]
        true_probs, _ = shin_method(odds)
        return true_probs

    shin_probs = matches.apply(calculate_shin_probs, axis=1, result_type="expand")
    shin_probs.columns = ["Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A"]
    matches = pd.concat([matches, shin_probs], axis=1)

    log_ok(
        f"Shin probabilities calculated. Found odds for {matches['Shin_Prob_H'].notna().sum()} matches."
    )
    # --- End: Shin Method Integration ---

    elo_ratings, elo_history = calculate_all_elo_ratings_batched(matches, BASE_ELO)
    elo_df = pd.DataFrame(elo_history).set_index("_temporal_row_id")
    matches = matches.set_index("_temporal_row_id")
    matches[["Home_Elo", "Away_Elo"]] = elo_df[["Home_Elo", "Away_Elo"]]
    matches = matches.reset_index()

    matches["GF"] = matches["HG"] if "HG" in matches.columns else 0
    matches["GA"] = matches["AG"] if "AG" in matches.columns else 0
    matches = compute_trailing_features_batched(matches, window=TRAILING_WINDOW, form_variant=form_variant)

    # Cold-start imputation: teams with fewer than window matches have NaN
    # trailing stats. Backfill with league means so these rows stay trainable
    # instead of being dropped by dropna(subset=FEATURE_COLUMNS).
    trailing_defaults = {
        "Home_Avg_GF": BASE_GOAL_RATE, "Away_Avg_GF": BASE_GOAL_RATE,
        "Home_Avg_GA": BASE_GOAL_RATE, "Away_Avg_GA": BASE_GOAL_RATE,
        "Home_Avg_GD": 0.0, "Away_Avg_GD": 0.0,
        "Home_Form": 1.0, "Away_Form": 1.0,
    }
    for col, default in trailing_defaults.items():
        if col in matches.columns:
            matches[col] = matches[col].fillna(default)
    if "Home_Matches" in matches.columns:
        matches["Home_Matches"] = matches["Home_Matches"].fillna(0)
    if "Away_Matches" in matches.columns:
        matches["Away_Matches"] = matches["Away_Matches"].fillna(0)

    log_info("Calculating Poisson features...")
    poisson_features = [
        calculate_poisson_features(
            r["Home_Elo"],
            r["Away_Elo"],
            r["Home_Avg_GF"],
            r["Away_Avg_GF"],
            r["Home_Avg_GA"],
            r["Away_Avg_GA"],
        )
        for _, r in matches.iterrows()
    ]
    matches = pd.concat(
        [matches, pd.DataFrame(poisson_features, index=matches.index)], axis=1
    )

    matches["Elo_Diff"] = matches["Home_Elo"] - matches["Away_Elo"]
    matches["Attack_Balance"] = matches["Home_Avg_GF"] - matches["Away_Avg_GF"]
    matches["Def_Balance"] = matches["Away_Avg_GA"] - matches["Home_Avg_GA"]
    matches["Form_Balance"] = matches["Home_Form"] - matches["Away_Form"]

    log_ok(f"Features built for {len(matches)} matches")

    return matches, elo_ratings


def train_validate(
    df: pd.DataFrame,
    features: List[str],
    model_type: str = MODEL_TYPE,
    n_splits: int = 5,
) -> Tuple[any, List[float], List[float]]:
    """Train model with time-series cross-validation.

    Args:
        df: DataFrame with all features
        features: List of feature column names
        model_type: Type of model ('lightgbm' or 'catboost')
        n_splits: Number of CV splits

    Returns:
        Tuple of (trained_model, cv_accuracies, cv_log_losses)
    """
    log_info(f"Training {model_type} model with {n_splits}-fold tournament-aware CV...")

    X, y = df[features].dropna(), df["Res"].loc[df[features].dropna().index]

    # Validate features before training
    feature_validation = validate_model_features(X, features)
    if not feature_validation.is_valid:
        log_error("Feature validation failed - aborting training")
        raise ValueError(f"Invalid features: {feature_validation.errors}")

    # Use sample weights to give more importance to non-draw outcomes
    # This helps the model learn to distinguish home/away wins better
    # without distorting the overall class distribution
    sample_weights = np.ones(len(y))
    class_counts = y.value_counts().sort_index()
    # Slightly downweight draws to reduce model's tendency to predict them
    # Weight ratio approximately 1.0 : 0.7 : 1.0 for Away : Draw : Home
    for idx, label in enumerate(y):
        if label == 1:  # Draw
            sample_weights[idx] = 0.7

    log_info(f"Using sample weights to reduce draw bias (Draw weight = 0.7)")

    model = create_model(model_type)
    # Tournament-aware CV using date gaps in df (which retains Date column).
    from src.cv_split import make_tournament_aware_cv
    try:
        splits = make_tournament_aware_cv(df, n_splits=n_splits, date_col="Date")
    except Exception:
        from sklearn.model_selection import TimeSeriesSplit
        splits = list(TimeSeriesSplit(n_splits=n_splits).split(df))
    cv_acc, cv_ll = [], []

    # Temporal Leakage Guard: Ensure X is sorted by time to prevent look-ahead bias in TimeSeriesSplit
    # Since df is passed in, we assume it maintains the sort order from load_data()
    # But we validate it here to be safe.
    log_info("Validating temporal order for CV splits...")
    # We check if the index is monotonically increasing (which corresponds to Date in our pipeline)
    if not np.all(np.diff(X.index) >= 0):
        log_error("Data indices are not monotonic! Potential temporal leakage detected.")
        raise ValueError("Data must be sorted by date before TimeSeriesSplit.")

    for fold, (t_idx, v_idx) in enumerate(splits, 1):
        f_model = create_model(model_type)
        # Early stopping: hold out last 10% of training fold as validation
        n_train = len(t_idx)
        val_size = max(1, n_train // 10)
        tr_idx, es_idx = t_idx[:-val_size], t_idx[-val_size:]
        try:
            f_model.fit(
                X.iloc[tr_idx], y.iloc[tr_idx],
                sample_weight=sample_weights[tr_idx],
                eval_set=[(X.iloc[es_idx], y.iloc[es_idx])],
                verbose=False,
            )
        except Exception:
            f_model.fit(X.iloc[t_idx], y.iloc[t_idx], sample_weight=sample_weights[t_idx])
        y_p = f_model.predict(X.iloc[v_idx])
        y_prob = f_model.predict_proba(X.iloc[v_idx])
        acc = accuracy_score(y.iloc[v_idx], y_p)
        ll = log_loss(y.iloc[v_idx], y_prob)
        cv_acc.append(acc)
        cv_ll.append(ll)
        log_info(f"Fold {fold} -> Acc: {acc:.3f}, LL: {ll:.3f}")

    model.fit(X, y, sample_weight=sample_weights)
    log_ok(f"Model trained. Mean Acc: {np.mean(cv_acc):.3f} (+/- {np.std(cv_acc):.3f})")

    return model, cv_acc, cv_ll


def predict_fixtures(
    fixtures: pd.DataFrame,
    elo_ratings: Dict,
    model: any,
    features: List[str],
    df_mean: Dict,
    historical_matches: pd.DataFrame,
    sofascore_data: Dict,
) -> pd.DataFrame:
    """Generate predictions for fixtures.

    Args:
        fixtures: DataFrame with fixture data
        elo_ratings: Dictionary of team Elo ratings
        model: Trained model
        features: List of feature column names
        df_mean: Mean feature values for fallback
        historical_matches: Historical match data for trailing stats
        sofascore_data: Sofascore standings data

    Returns:
        DataFrame with predictions
    """
    if fixtures.empty:
        return fixtures

    log_info(f"Generating predictions for {len(fixtures)} fixtures...")

    fixtures = predict_gameweek(
        fixtures,
        elo_ratings,
        model,
        features,
        df_mean,
        historical_matches,
        sofascore_data,
    )

    log_ok("Predictions generated")

    return fixtures


def format_match_prediction(row: pd.Series) -> str:
    """Format single fixture prediction into probability distribution report."""
    raw_h = row["Raw_Home"] if pd.notna(row.get("Raw_Home")) else row.get("HomeTeam", row.get("Home", "Home"))
    raw_a = row["Raw_Away"] if pd.notna(row.get("Raw_Away")) else row.get("AwayTeam", row.get("Away", "Away"))
    home_name = re.sub(r":.*$", "", str(raw_h)).strip()
    away_name = re.sub(r":.*$", "", str(raw_a)).strip()

    # Canonical encoding: 0=Away, 1=Draw, 2=Home
    p_a = float(row.get("Pred_Proba_Away", 0.0))
    p_d = float(row.get("Pred_Proba_Draw", 0.0))
    p_h = float(row.get("Pred_Proba_Home", 0.0))

    # Top pick determination
    if p_h >= p_d and p_h >= p_a:
        top_outcome = "Home"
        top_prob = p_h
    elif p_a >= p_h and p_a >= p_d:
        top_outcome = "Away"
        top_prob = p_a
    else:
        top_outcome = "Draw"
        top_prob = p_d

    if top_prob >= CONFIDENCE_STRONG_THRESHOLD:
        confidence = "Strong"
    elif top_prob >= CONFIDENCE_MODERATE_THRESHOLD:
        confidence = "Moderate"
    else:
        confidence = "Marginal"

    top_pick_str = f"{top_outcome} ({confidence})"

    # Market implied probabilities if available
    has_shin = (
        pd.notna(row.get("Shin_Prob_Home"))
        and pd.notna(row.get("Shin_Prob_Away"))
        and pd.notna(row.get("Shin_Prob_Draw"))
        and not (
            abs(float(row.get("Shin_Prob_Home", 0.0)) - 1 / 3) < 1e-4
            and abs(float(row.get("Shin_Prob_Away", 0.0)) - 1 / 3) < 1e-4
        )
    )
    if has_shin:
        m_a = float(row["Shin_Prob_Away"]) * 100
        m_d = float(row["Shin_Prob_Draw"]) * 100
        m_h = float(row["Shin_Prob_Home"]) * 100
        market_str = f"P(Away): {m_a:.1f}% | P(Draw): {m_d:.1f}% | P(Home): {m_h:.1f}%"
    else:
        market_str = "[Not available]"

    lines = [
        f"Match: {home_name} vs {away_name}",
        f"P(Away): {p_a*100:.1f}% | P(Draw): {p_d*100:.1f}% | P(Home): {p_h*100:.1f}%",
        f"Market Implied: {market_str}",
        f"Top Pick: {top_pick_str}",
        "---",
    ]
    return "\n".join(lines)


def write_outputs(
    fixtures: pd.DataFrame, feature_importance: pd.DataFrame, output_dir: str = "."
) -> str:
    """Save predictions and generate reports.

    Args:
        fixtures: DataFrame with predictions
        feature_importance: DataFrame with feature importances
        output_dir: Directory for output files

    Returns:
        Path to results file
    """
    today = datetime.now().strftime("%Y%m%d")

    feature_importance_path = os.path.join(
        output_dir, f"feature_importance_{today}.png"
    )
    fig = None
    try:
        fig = plt.figure(figsize=(12, 8))
        plt.barh(
            feature_importance["feature"],
            feature_importance["importance"],
            color=[
                "coral" if "Poisson" in f or "xG" in f else "steelblue"
                for f in feature_importance["feature"]
            ],
        )
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(feature_importance_path, dpi=150)
    finally:
        if fig is not None:
            plt.close(fig)
    log_ok(f"Feature importance chart saved: {feature_importance_path}")

    output_file = os.path.join(output_dir, f"Resultados_{today}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            "=" * 60 + "\n  PREDICCIONES - LIGA PROFESIONAL ARGENTINA (PROBABILITY ENGINE)\n" + "=" * 60 + "\n\n"
        )
        for _, row in fixtures.iterrows():
            f.write(format_match_prediction(row) + "\n")

        f.write(f"\n{'='*60}\nRESUMEN\n{'='*60}\n")
        f.write(f"Partidos: {len(fixtures)}\n")

    log_ok(f"Results saved to {output_file}")

    return output_file


def run_pipeline(
    glossary_path: str = "Glossary.txt",
    sofascore_path: str = "src/sofascore_stats.json",
    fixtures_path: str = "partidos.txt",
    historical_path: str = "data/ARG.csv",
    model_type: str = MODEL_TYPE,
    output_dir: str = ".",
) -> PipelineResult:
    """Execute the full prediction pipeline.

    Args:
        glossary_path: Path to team name glossary
        sofascore_path: Path to Sofascore standings JSON
        fixtures_path: Path to fixtures file
        historical_path: Path to historical match data CSV
        model_type: Type of model to use
        output_dir: Directory for output files

    Returns:
        PipelineResult with all outputs
    """
    log_info("=" * 60)
    log_info("ML_Predictor2026_V2 - Poisson Distribution Enhanced")
    log_info("=" * 60)

    result = PipelineResult()

    try:
        glossary, sofascore_data, matches, fixtures = load_data(
            glossary_path, sofascore_path, fixtures_path, historical_path
        )

        matches_with_features, elo_ratings = build_features(matches)

        df = matches_with_features.dropna(subset=FEATURE_COLUMNS).copy()

        model, cv_acc, cv_ll = train_validate(df, FEATURE_COLUMNS, model_type)
        result.model = model
        result.cv_accuracies = cv_acc
        result.cv_log_losses = cv_ll
        result.elo_ratings = elo_ratings
        result.features = FEATURE_COLUMNS

        feature_importance = (
            pd.DataFrame(
                {"feature": FEATURE_COLUMNS, "importance": model.feature_importances_}
            )
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        result.feature_importance = feature_importance

        if not fixtures.empty:
            df_mean = df[FEATURE_COLUMNS].mean().to_dict()
            fixtures = predict_fixtures(
                fixtures,
                elo_ratings,
                model,
                FEATURE_COLUMNS,
                df_mean,
                matches_with_features,
                sofascore_data,
            )
            result.fixtures = fixtures

            output_file = write_outputs(fixtures, feature_importance, output_dir)
            result.output_file = output_file

        return result

    except Exception as e:
        log_error(f"Pipeline failed: {e}")
        raise
