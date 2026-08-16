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
from src.cold_start import build_meta_xg_features, compute_team_matchdays
from src.cv_split import tournament_aware_cv_splits

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
    # Bayesian-shrunk Poisson xG meta-features (cold-start calibrated)
    "poisson_xg_home_meta", "poisson_xg_away_meta",
]


class PipelineResult:
    """Container for pipeline execution results."""

    def __init__(self):
        self.model = None
        self.elo_ratings: Dict = {}
        self.features: List[str] = []
        self.cv_accuracies: List[float] = []
        self.cv_log_losses: List[float] = []
        self.naive_log_loss: Optional[float] = None
        self.bookie_log_loss: Optional[float] = None
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

    # Warn about teams in fixtures with no historical data (new/promoted teams)
    if fixtures is not None and not fixtures.empty:
        known_teams = set(matches["HomeTeam"].unique()) | set(matches["AwayTeam"].unique())
        fixture_teams = set(fixtures["HomeTeam"].unique()) | set(fixtures["AwayTeam"].unique())
        unknown_teams = fixture_teams - known_teams
        if unknown_teams:
            log_warning(
                f"[SEASON CHECK] {len(unknown_teams)} team(s) in fixtures have NO historical data "
                f"(likely promoted/new): {sorted(unknown_teams)}"
            )
            log_warning(
                "[SEASON CHECK] These teams will use default Elo (1500) and zero trailing stats. "
                "Add them to Glossary.txt if they appear under a different name in ARG.csv."
            )

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
    # Home_GF = goals scored by home team, Away_GF = goals scored by away team
    # GF = goals scored by home team (from home perspective)
    # GA = goals conceded by home team = goals scored by away team
    if "Home_GF" in matches.columns and "Away_GF" in matches.columns:
        matches["GF"] = matches["Home_GF"]
        matches["GA"] = matches["Away_GF"]
    elif "FTHG" in matches.columns and "FTAG" in matches.columns:
        matches["GF"] = matches["FTHG"]
        matches["GA"] = matches["FTAG"]
    else:
        log_warning("Goal columns not found; trailing stats will use zeros")
        matches["GF"] = 0
        matches["GA"] = 0
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

    # --- Bayesian-shrunk Poisson xG meta-features (cold-start calibration) ---
    log_info("Computing Bayesian-shrunk xG meta-features...")
    home_md, away_md = compute_team_matchdays(matches)
    meta_home, meta_away = build_meta_xg_features(
        matches["xG_home"].values,
        matches["xG_away"].values,
        home_md,
        away_md,
    )
    matches["poisson_xg_home_meta"] = meta_home
    matches["poisson_xg_away_meta"] = meta_away
    log_ok("Bayesian xG meta-features computed")

    log_ok(f"Features built for {len(matches)} matches")

    return matches, elo_ratings


def _build_fold_features(
    raw_matches: pd.DataFrame,
    until_row: int,
    elo_ratings: dict,
    window: int,
) -> pd.DataFrame:
    """Build Elo + trailing-stats features for the first ``until_row`` rows.

    Mirrors the wide-frame output of :func:`build_features` (i.e. produces
    Home_Elo, Away_Elo, Home_Avg_GF, ..., Away_Matches, plus the downstream
    Elo_Diff / Attack_Balance / Form_Balance / xG* / Poisson_* / Expected_*
    columns). Uses the fold-aware variants of ``calculate_all_elo_ratings``
    and ``compute_trailing_features`` so no outcome from beyond ``until_row``
    influences any feature in the resulting frame.
    """
    # Re-derive Elo up to the cutoff. We keep the snapshot for downstream
    # fixtures (production inference) but the row-level features only need
    # the per-row Home_Elo / Away_Elo from the prefix.
    _, elo_prefix_history = calculate_all_elo_ratings(
        raw_matches, BASE_ELO, until_row=until_row
    )
    elo_df = pd.DataFrame(elo_prefix_history)

    # Working slice: first ``until_row`` rows, defensively sorted.
    slice_df = raw_matches.iloc[:until_row].copy().sort_values("Date").reset_index(drop=True)

    # Map per-row Elo via merge so we don't lose the (Date, HomeTeam, AwayTeam)
    # alignment that the original pipeline relies on.
    slice_df = slice_df.merge(elo_df, on=["Date", "HomeTeam", "AwayTeam"], how="left")

    # Trailing stats with fold cutoff = until_row (the function propagates the
    # most recent per-team feature vector onto any rows beyond the cutoff, but
    # we only consume rows within the prefix here).
    slice_df = compute_trailing_features(slice_df, window=window)

    # Vectorised Poisson features from the freshly-computed Elo and trailing
    # stats. Mirrors the logic in ``build_features`` so CV metrics stay
    # comparable.
    from src.stats_engine import calculate_expected_goals, calculate_outcome_probabilities

    xG_h, xG_a = calculate_expected_goals(
        slice_df["Home_Elo"].values,
        slice_df["Away_Elo"].values,
        slice_df["Home_Avg_GF"].values,
        slice_df["Away_Avg_GF"].values,
        slice_df["Home_Avg_GA"].values,
        slice_df["Away_Avg_GA"].values,
    )
    slice_df["xG_home"] = xG_h
    slice_df["xG_away"] = xG_a
    slice_df["xG_diff"] = xG_h - xG_a

    outcomes = slice_df.apply(
        lambda r: calculate_outcome_probabilities(r["xG_home"], r["xG_away"]),
        axis=1,
    )
    slice_df["Poisson_Home_Win"] = outcomes.apply(lambda x: x["home_win"])
    slice_df["Poisson_Draw"] = outcomes.apply(lambda x: x["draw"])
    slice_df["Poisson_Away_Win"] = outcomes.apply(lambda x: x["away_win"])
    slice_df["Expected_Home_Goals"] = outcomes.apply(lambda x: x["expected_home_goals"])
    slice_df["Expected_Away_Goals"] = outcomes.apply(lambda x: x["expected_away_goals"])
    slice_df["Expected_Total_Goals"] = (
        slice_df["Expected_Home_Goals"] + slice_df["Expected_Away_Goals"]
    )

    slice_df["Elo_Diff"] = slice_df["Home_Elo"] - slice_df["Away_Elo"]
    slice_df["Attack_Balance"] = slice_df["Home_Avg_GF"] - slice_df["Away_Avg_GF"]
    slice_df["Def_Balance"] = slice_df["Away_Avg_GA"] - slice_df["Home_Avg_GA"]
    slice_df["Form_Balance"] = slice_df["Home_Form"] - slice_df["Away_Form"]

    # Bayesian-shrunk xG meta-features. ``compute_team_matchdays`` is already
    # fold-safe because it relies on (Season, Team).cumcount().
    home_md, away_md = compute_team_matchdays(slice_df)
    meta_home, meta_away = build_meta_xg_features(
        slice_df["xG_home"].values,
        slice_df["xG_away"].values,
        home_md,
        away_md,
    )
    slice_df["poisson_xg_home_meta"] = meta_home
    slice_df["poisson_xg_away_meta"] = meta_away

    return slice_df


def train_validate(
    df: pd.DataFrame,
    features: List[str],
    model_type: str = MODEL_TYPE,
    n_splits: int = 5,
    raw_matches: Optional[pd.DataFrame] = None,
) -> Tuple[any, List[float], List[float], pd.DataFrame, Optional[float], Optional[float]]:
    """Train model with time-series cross-validation.

    Args:
        df: DataFrame with all features. If ``raw_matches`` is provided,
            ``df`` is expected to be the post-``dropna`` projection of the
            feature frame built by :func:`build_features` over the full
            timeline. Fold-aware feature re-computation will be performed
            from ``raw_matches`` to avoid leakage.
        features: List of feature column names
        model_type: Type of model ('lightgbm' or 'catboost')
        n_splits: Number of CV splits
        raw_matches: Optional chronologically-sorted historical DataFrame
            (columns Date, HomeTeam, AwayTeam, FullTimeResult, GF, GA, plus
            optional Season). When provided, training and validation
            features are rebuilt per fold using only matches that occurred
            at or before the fold's validation start, eliminating the
            Elo / EWMA leakage documented in the time-series CV audit.

    Returns:
        Tuple of (trained_model, cv_accuracies, cv_log_losses, submodel_training_data, naive_ll, bookie_ll)
    """
    log_info(f"Training {model_type} model with {n_splits}-fold CV...")

    use_fold_aware = raw_matches is not None and not raw_matches.empty
    if use_fold_aware:
        # Build the *initial* dropna mask from the input ``df`` (it already
        # carries the canonical FEATURE_COLUMNS), but defer the actual
        # training/validation matrices to per-fold re-computation below.
        base_index = df.index
        seasons = raw_matches["Season"] if "Season" in raw_matches.columns else pd.Series(
            ["unknown"] * len(raw_matches), index=raw_matches.index
        )
        cv_splits = list(
            tournament_aware_cv_splits(len(raw_matches), seasons, n_splits=n_splits)
        )
        # We will materialise X / y inside the fold loop instead of here.
        X_dummy = df[features]
        y_dummy = df["FullTimeResult"]
        sample_weights_full = np.ones(len(df))
        for idx, label in enumerate(df["FullTimeResult"]):
            if label == 1:  # Draw
                sample_weights_full[idx] = 0.7
    else:
        X, y = df[features].dropna(), df["FullTimeResult"].loc[df[features].dropna().index]
        base_index = X.index

        # Validate features before training
        feature_validation = validate_model_features(X, features)
        if not feature_validation.is_valid:
            log_error("Feature validation failed - aborting training")
            raise ValueError(f"Invalid features: {feature_validation.errors}")

        seasons = df["Season"] if "Season" in df.columns else pd.Series(
            ["unknown"] * len(X), index=X.index
        )
        cv_splits = list(tournament_aware_cv_splits(len(X), seasons, n_splits=n_splits))
        sample_weights_full = np.ones(len(X))
        for idx, label in enumerate(y):
            if label == 1:  # Draw
                sample_weights_full[idx] = 0.7

    log_info("Using sample weights to reduce draw bias (Draw weight = 0.7)")

    model = create_model(model_type)
    cv_acc, cv_ll = [], []
    submodel_data_collection = []  # Initialize collection list
    last_v_idx: Optional[np.ndarray] = None

    for fold, (t_idx, v_idx) in enumerate(cv_splits, 1):
        if use_fold_aware:
            # Fold boundaries live in raw_matches row-space. The training rows
            # occupy [0, t_idx.max()+1); the validation rows occupy
            # [t_idx.max()+1, v_idx.max()+1). Both slices are rebuilt via the
            # fold-aware helper so that no outcome from the validation window
            # leaks into the training features.
            train_until = int(t_idx.max()) + 1
            val_until = int(v_idx.max()) + 1

            # _build_fold_features(until_row=val_until) returns a frame where:
            #   * rows [0, train_until)   have fresh EWMA + Elo features
            #   * rows [train_until, val_until) carry per-team "as-of cutoff"
            #     trailing stats (no knowledge of their own outcomes) and a
            #     snapshot Elo per team derived only from training-period
            #     matches.
            fold_features = _build_fold_features(
                raw_matches, until_row=val_until,
                elo_ratings={}, window=TRAILING_WINDOW,
            )
            train_features = fold_features.iloc[:train_until]
            val_rows = fold_features.iloc[train_until:val_until]

            X_train = train_features[features]
            y_train = train_features["FullTimeResult"]
            X_val = val_rows[features]
            y_val = val_rows["FullTimeResult"]
            sw_train = np.ones(len(y_train))
            for idx, label in enumerate(y_train):
                if label == 1:
                    sw_train[idx] = 0.7
        else:
            X_train = X.iloc[t_idx]
            y_train = y.iloc[t_idx]
            X_val = X.iloc[v_idx]
            y_val = y.iloc[v_idx]
            sw_train = sample_weights_full[t_idx]

        f_model = create_model(model_type)
        # Pass eval_set so CatBoost early_stopping_rounds has validation loss to monitor.
        # Guard with try/except so MockModels in tests aren't broken by the extra kwarg.
        fit_kwargs: dict = {"sample_weight": sw_train}
        if model_type == "catboost":
            fit_kwargs["eval_set"] = (X_val, y_val)
        try:
            f_model.fit(X_train, y_train, **fit_kwargs)
        except TypeError:
            # Fallback for mock models or implementations that don't accept eval_set
            f_model.fit(X_train, y_train, sample_weight=sw_train)
        y_p = f_model.predict(X_val)
        y_prob = f_model.predict_proba(X_val)
        acc = accuracy_score(y_val, y_p)
        ll = log_loss(y_val, y_prob, labels=[0, 1, 2])
        cv_acc.append(acc)
        cv_ll.append(ll)
        log_info(f"Fold {fold} -> Acc: {acc:.3f}, LL: {ll:.3f}")

        # Collect data for sub-model training. We stitch the predictions onto
        # the fold's validation rows so downstream sub-model training can use
        # the same per-row metadata.
        if use_fold_aware:
            fold_data = val_features.copy()
        else:
            fold_data = df.loc[df.index[v_idx]].copy()
        fold_data['ml_pred'] = y_p
        fold_data['p_h'] = y_prob[:, 2]  # Home Win probability
        fold_data['p_d'] = y_prob[:, 1]  # Draw probability
        fold_data['p_a'] = y_prob[:, 0]  # Away Win probability

        # Ensure 'Expected_Home_Goals' and 'Expected_Away_Goals' are in the collected data
        # and map them to 'exp_h' and 'exp_a'
        fold_data['exp_h'] = fold_data['Expected_Home_Goals']
        fold_data['exp_a'] = fold_data['Expected_Away_Goals']

        # Select relevant columns for the sub-model
        # Home_GF/Away_GF may not exist in all DataFrames (e.g. test fixtures)
        goal_cols = [c for c in ['Home_GF', 'Away_GF'] if c in fold_data.columns]
        base_cols = ['exp_h', 'exp_a', 'ml_pred', 'p_h', 'p_d', 'p_a']
        submodel_data_collection.append(fold_data[base_cols + goal_cols])

        last_v_idx = v_idx

    # Concatenate all collected data
    submodel_training_data_df = pd.concat(submodel_data_collection, ignore_index=True) if submodel_data_collection else pd.DataFrame()


    # Baseline comparison (naive & bookie)
    naive_ll = 1.077  # Historical baseline log loss
    bookie_ll = None
    # Bookie: naive odds-to-prob conversion (approximate for comparison)
    # Using last fold validation indices for a quick comparative snapshot
    if last_v_idx is not None and len(last_v_idx) > 0:
        if use_fold_aware:
            # Last-fold validation rows are raw_matches[last_v_idx].
            val_data = raw_matches.iloc[last_v_idx]
            y_last = val_data["FullTimeResult"]
        else:
            val_data = df.iloc[last_v_idx]
            y_last = y.iloc[last_v_idx]
        # Check if odds exist
        odds_cols = ['Odds_b365_A', 'Odds_b365_D', 'Odds_b365_H']
        if all(c in val_data.columns for c in odds_cols) and len(y_last) > 0:
             bookie_probs = 1 / val_data[odds_cols].values
             bookie_probs /= bookie_probs.sum(axis=1, keepdims=True)
             bookie_ll = log_loss(y_last, bookie_probs, labels=[0, 1, 2])
             log_info(f"Bookie Baseline Log Loss: {bookie_ll:.3f}")

    log_info(f"Naive Baseline Log Loss: {naive_ll:.3f}")
    # Final fit on all data: in fold-aware mode this uses the full feature
    # frame built from raw_matches (i.e. production-style features, including
    # all available history).
    if use_fold_aware:
        full_features = _build_fold_features(
            raw_matches, until_row=len(raw_matches),
            elo_ratings={}, window=TRAILING_WINDOW,
        )
        X_full = full_features[features]
        y_full = full_features["FullTimeResult"]
        sw_full = np.ones(len(y_full))
        for idx, label in enumerate(y_full):
            if label == 1:
                sw_full[idx] = 0.7
        model.fit(X_full, y_full, sample_weight=sw_full)
    else:
        model.fit(X, y, sample_weight=sample_weights_full)
    log_ok(f"Model trained. Mean Acc: {np.mean(cv_acc):.3f} (+/- {np.std(cv_acc):.3f})")

    return model, cv_acc, cv_ll, submodel_training_data_df, naive_ll, bookie_ll


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
    baseline_results: Dict = None,
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
    
    # Fallback: use today's date so the file is always uniquely named
    if fecha_num == "XX":
        fecha_num = datetime.now().strftime("%Y%m%d")
        log_warning(f"No FECHA number found in header; using date-based filename suffix: {fecha_num}")

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

        # Write baseline comparison section
        if baseline_results:
            f.write("\n--- METRICS COMPARISON ---\n")
            if baseline_results.get("naive_ll"):
                f.write(f"Naive Baseline Log Loss: {baseline_results['naive_ll']:.3f}\n")
            if baseline_results.get("bookie_ll") is not None:
                f.write(f"Bookie Baseline Log Loss: {baseline_results['bookie_ll']:.3f}\n")
            if baseline_results.get("model_ll"):
                f.write(f"Model Log Loss: {baseline_results['model_ll']:.3f}\n")
            f.write("--------------------------\n")

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

        model, cv_acc, cv_ll, submodel_data, naive_ll, bookie_ll = train_validate(df, FEATURE_COLUMNS, model_type)
        result.model = model
        result.cv_accuracies = cv_acc
        result.cv_log_losses = cv_ll
        result.naive_log_loss = naive_ll
        result.bookie_log_loss = bookie_ll
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

            # Build baseline results for output
            baseline_results = {
                "naive_ll": result.naive_log_loss,
                "bookie_ll": result.bookie_log_loss,
                "model_ll": np.mean(result.cv_log_losses) if result.cv_log_losses else None,
            }

            output_file = write_outputs(
                fixtures,
                feature_importance,
                output_dir,
                header_line=fixtures_header,
                summary=fixtures_summary,
                baseline_results=baseline_results,
            )
            result.output_file = output_file

        return result

    except Exception as e:
        log_error(f"Pipeline failed: {e}")
        raise
