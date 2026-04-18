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
from sklearn.model_selection import TimeSeriesSplit

from src.config import BASE_ELO, MODEL_TYPE, TRAILING_WINDOW, RESULT_ENCODING
from src.utils import log_info, log_ok, log_error, log_warning
from src.data_ingestion import DataIngestor
from src.data_processing import (
    load_glossary, load_sofascore_data, normalize_team_name,
    clean_partidos_file, parse_fixtures, apply_header_mapping
)
from src.stats_engine import (
    calculate_all_elo_ratings,
    calculate_poisson_features,
    shin_method,
)
from src.features import compute_trailing_features
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
    fixtures_path: str = "Partidos.txt",
    historical_path: str = "data/ARG.csv"
) -> Tuple[Dict, Dict, pd.DataFrame, Optional[pd.DataFrame], Optional[str], Optional[Dict]]:
    """Load and normalize all input data.

    Args:
        glossary_path: Path to team name glossary
        sofascore_path: Path to Sofascore standings JSON
        fixtures_path: Path to fixtures file
        historical_path: Path to historical match data CSV

    Returns:
        Tuple of (glossary, sofascore_data, matches_df, fixtures_df, fixtures_header, fixtures_summary)
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
        
        # Apply canonical header mapping
        matches, mapping_log = apply_header_mapping(matches)
        
        # Validate required columns exist
        required_cols = ["HomeTeam", "AwayTeam", "FullTimeResult", "Date"]
        missing_cols = [col for col in required_cols if col not in matches.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        matches = matches.dropna(subset=["HomeTeam", "AwayTeam", "FullTimeResult"])
        matches = matches.dropna(subset=["Date"])
        matches["Date"] = pd.to_datetime(matches["Date"], dayfirst=True, errors="coerce")
        matches["HomeTeam"] = matches["HomeTeam"].map(lambda x: normalize_team_name(x, glossary))
        matches["AwayTeam"] = matches["AwayTeam"].map(lambda x: normalize_team_name(x, glossary))
        matches["FullTimeResult"] = matches["FullTimeResult"].map(RESULT_ENCODING)
        
        # Validate result encoding - warn if any unmapped results
        if matches["FullTimeResult"].isna().any():
            unmapped_count = matches["FullTimeResult"].isna().sum()
            log_warning(f"{unmapped_count} matches have invalid result codes (not H/D/A)")
        
        matches = matches.sort_values("Date").reset_index(drop=True)
        log_ok(f"Historical matches loaded: {len(matches)}")
    except Exception as e:
        log_error(f"Error reading historical data: {e}")
        raise

    fixtures, fixtures_header, fixtures_summary = parse_fixtures(fixtures_path, glossary)

    # Run validation checks
    is_valid, errors = validate_pipeline_inputs(glossary, matches, fixtures, sofascore_data)
    if not is_valid:
        log_warning("Data validation completed with warnings/errors (see above)")

    return glossary, sofascore_data, matches, fixtures, fixtures_header, fixtures_summary


def build_features(matches: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Compute all features for model training.

    Args:
        matches: DataFrame with normalized match data

    Returns:
        Tuple of (feature_dataframe, elo_ratings_dict)
    """
    log_info("Building features...")

    # --- Start: Shin Method Integration ---
    log_info("Calculating Shin Method probabilities from odds...")

    def calculate_shin_probs(row):
        """Helper to apply shin_method to a row."""
        # Use canonical odds headers if available, fallback to B365CH etc if they weren't mapped
        odds_cols = ["Odds_b365_H", "Odds_b365_D", "Odds_b365_A"]
        # Fallback if mapping missed them or they are already B365CH
        if not all(c in row for c in odds_cols):
            fallback_cols = ["B365CH", "B365CD", "B365CA"]
            if all(c in row for c in fallback_cols):
                odds_cols = fallback_cols
            else:
                return [np.nan, np.nan, np.nan]

        if not all(pd.notna(row[c]) for c in odds_cols):
            return [np.nan, np.nan, np.nan]

        odds = [row[odds_cols[0]], row[odds_cols[1]], row[odds_cols[2]]]
        true_probs, _ = shin_method(odds)
        return true_probs

    shin_probs = matches.apply(calculate_shin_probs, axis=1, result_type="expand")
    shin_probs.columns = ["Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A"]
    matches = pd.concat([matches, shin_probs], axis=1)

    log_ok(
        f"Shin probabilities calculated. Found odds for {matches['Shin_Prob_H'].notna().sum()} matches."
    )
    # --- End: Shin Method Integration ---

    elo_ratings, elo_history = calculate_all_elo_ratings(matches, BASE_ELO)
    elo_df = pd.DataFrame(elo_history)
    matches = matches.merge(elo_df, on=["Date", "HomeTeam", "AwayTeam"], how="left")

    # Map goals to internal processing names for trailing features
    matches["GF"] = matches["Home_GF"] if "Home_GF" in matches.columns else 0
    matches["GA"] = matches["Away_GF"] if "Away_GF" in matches.columns else 0
    matches = compute_trailing_features(matches, window=TRAILING_WINDOW)

    log_info("Calculating Poisson features...")
    # Vectorized xG calculation
    from src.stats_engine import calculate_expected_goals, calculate_outcome_probabilities
    
    xG_h, xG_a = calculate_expected_goals(
        matches["Home_Elo"].values,
        matches["Away_Elo"].values,
        matches["Home_Avg_GF"].values,
        matches["Away_Avg_GF"].values,
        matches["Home_Avg_GA"].values,
        matches["Away_Avg_GA"].values,
    )
    matches["xG_home"] = xG_h
    matches["xG_away"] = xG_a
    matches["xG_diff"] = xG_h - xG_a

    # Outcome probabilities (using apply for the complex grid logic)
    outcomes = matches.apply(lambda r: calculate_outcome_probabilities(r["xG_home"], r["xG_away"]), axis=1)
    
    matches["Poisson_Home_Win"] = outcomes.apply(lambda x: x["home_win"])
    matches["Poisson_Draw"] = outcomes.apply(lambda x: x["draw"])
    matches["Poisson_Away_Win"] = outcomes.apply(lambda x: x["away_win"])
    matches["Expected_Home_Goals"] = outcomes.apply(lambda x: x["expected_home_goals"])
    matches["Expected_Away_Goals"] = outcomes.apply(lambda x: x["expected_away_goals"])
    matches["Expected_Total_Goals"] = matches["Expected_Home_Goals"] + matches["Expected_Away_Goals"]

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
    log_info(f"Training {model_type} model with {n_splits}-fold CV...")

    X, y = df[features].dropna(), df["FullTimeResult"].loc[df[features].dropna().index]
    
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
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_acc, cv_ll = [], []

    for fold, (t_idx, v_idx) in enumerate(tscv.split(X), 1):
        f_model = create_model(model_type)
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
    header_line: str = None,
    summary: Dict = None,
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


from src.summary_validator import validate_and_fix_summary

def write_outputs(
    fixtures: pd.DataFrame,
    feature_importance: pd.DataFrame,
    output_dir: str = ".",
    header_line: str = None,
    summary: Dict = None,
) -> str:
    """Save predictions and generate reports.

    Args:
        fixtures: DataFrame with predictions
        feature_importance: DataFrame with feature importances
        output_dir: Directory for output files
        header_line: Header line from fixtures file (e.g., "FECHA 13 - 01 al 06042026")
        summary: Dictionary with summary values (penales, expulsados, goles)

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

    # Extract fecha number from header for output filename
    fecha_num = "XX"
    if header_line:
        m = re.search(r"FECHA\s+(\d+)", header_line, re.IGNORECASE)
        if m:
            fecha_num = m.group(1)

    output_file = os.path.join(output_dir, f"PrediccionFecha{fecha_num}.txt")

    # Validate and fix summary stats (PDF Fallback)
    penales = summary.get('penales', 0) if summary else 0
    expulsados = summary.get('expulsados', 0) if summary else 0
    total_model_goals = 0
    for _, row in fixtures.iterrows():
        total_model_goals += int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6)) + int(np.clip(row.get("Pred_Away_Goals", 0), 0, 6))

    penales, expulsados, _ = validate_and_fix_summary(penales, expulsados, total_model_goals)

    with open(output_file, "w", encoding="utf-8") as f:
        # Write header
        if header_line:
            f.write(header_line + "\n")
        else:
            f.write(f"FECHA {fecha_num}\n")

        # Write matches with predicted scores
        for _, row in fixtures.iterrows():
            hg = int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6))
            ag = int(np.clip(row.get("Pred_Away_Goals", 0), 0, 6))
            f.write(f"{row.get('Raw_Home', row['HomeTeam'])} - {row.get('Raw_Away', row['AwayTeam'])}: {hg}-{ag}\n")

        # Write summary section
        f.write(f"Cantidad de penales cobrados: {penales}\n")
        f.write(f"Cantidad de expulsados: {expulsados}\n")
        f.write(f"Cantidad de goles convertidos: {total_model_goals}\n")

    log_ok(f"Results saved to {output_file}")

    return output_file


def run_pipeline(
    glossary_path: str = "Glossary.txt",
    sofascore_path: str = "src/sofascore_stats.json",
    fixtures_path: str = "Partidos.txt",
    historical_path: str = "data/ARG.csv",
    model_type: str = MODEL_TYPE,
    output_dir: str = ".",
    auto_update: bool = True
) -> PipelineResult:
    """Execute the full prediction pipeline.

    Args:
        glossary_path: Path to team name glossary
        sofascore_path: Path to Sofascore standings JSON
        fixtures_path: Path to fixtures file
        historical_path: Path to historical match data CSV
        model_type: Type of model to use
        output_dir: Directory for output files
        auto_update: Whether to automatically check for and apply data updates

    Returns:
        PipelineResult with all outputs
    """
    log_info("=" * 60)
    log_info("ML_Predictor2026_V2 - Poisson Distribution Enhanced")
    log_info("=" * 60)

    # --- Step 0: Data Ingestion/Update ---
    if auto_update:
        try:
            ingestor = DataIngestor(data_path=historical_path)
            if ingestor.update_base_data():
                log_ok("Base historical data updated from football-data.co.uk")
            ingestor.enrich_with_api_stats()
        except Exception as e:
            log_warning(f"Data update failed (skipping): {e}")
    # --- End Step 0 ---

    result = PipelineResult()

    try:
        glossary, sofascore_data, matches, fixtures, fixtures_header, fixtures_summary = load_data(
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
                header_line=fixtures_header,
                summary=fixtures_summary,
            )
            result.fixtures = fixtures

            output_file = write_outputs(
                fixtures,
                feature_importance,
                output_dir,
                header_line=fixtures_header,
                summary=fixtures_summary,
            )
            result.output_file = output_file

        return result

    except Exception as e:
        log_error(f"Pipeline failed: {e}")
        raise
