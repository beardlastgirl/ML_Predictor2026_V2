# Architecture

**Analysis Date:** 2025-03-20

## Pattern Overview

**Overall:** Pipeline-based data processing and machine learning prediction system with modular separation of concerns.

**Key Characteristics:**
- **Linear Pipeline Flow:** Data ingestion → Normalization → Feature Engineering → Model Training → Prediction → Output
- **Modular Service Layer:** Core logic isolated in `src/` package modules with single responsibilities
- **Functional Decomposition:** Pure functions for calculations (Elo, Poisson, statistics) versus orchestration in pipeline
- **Time-Series Cross-Validation:** Uses temporal data splits to prevent data leakage in historical model training
- **Ensemble Features:** Combines multiple feature sources (Elo, trailing stats, Poisson probabilities, Sofascore)

## Layers

**Pipeline Orchestration Layer:**
- Purpose: Coordinates end-to-end execution flow
- Location: `main.py`, `src/pipeline.py`
- Contains: Pipeline stages, stage orchestration, result aggregation
- Depends on: All service modules (data_processing, stats_engine, features, model_engine)
- Used by: Entry point (`main.py`) and PowerShell runner (`run_model.ps1`)

**Data Loading and Normalization Layer:**
- Purpose: Ingest and normalize heterogeneous data sources
- Location: `src/data_processing.py`
- Contains: Glossary loading, Sofascore JSON parsing, fixture parsing, team name normalization
- Depends on: Filesystem access, utilities logging
- Used by: Pipeline's `load_data()` stage

**Statistical Computation Layer:**
- Purpose: Calculate Elo ratings and Poisson goal probabilities
- Location: `src/stats_engine.py`
- Contains: Pure functions for Elo updates, expected goals, Poisson distribution, match outcome probabilities
- Depends on: scipy.stats.poisson, numpy
- Used by: Feature building stage, model prediction stage

**Feature Engineering Layer:**
- Purpose: Transform raw statistics into ML-ready features
- Location: `src/features.py`
- Contains: Trailing average calculations, team history tracking, feature aggregation
- Depends on: stats_engine for Poisson features, pandas for DataFrame operations
- Used by: Pipeline's `build_features()` stage, model prediction stage

**Model Training and Prediction Layer:**
- Purpose: Train gradient boosting models and generate fixture predictions
- Location: `src/model_engine.py`
- Contains: Model instantiation (CatBoost/LightGBM), prediction logic, feature preparation
- Depends on: sklearn.model_selection.TimeSeriesSplit, features layer, stats_engine
- Used by: Pipeline's training and prediction stages

**Configuration Layer:**
- Purpose: Centralize all hyperparameters and constants
- Location: `src/config.py`
- Contains: Elo parameters, Poisson parameters, feature columns, model hyperparameters, thresholds
- Depends on: Environment variables (ML_PREDICTOR_MODEL)
- Used by: All other modules for consistent parameterization

**Utilities Layer:**
- Purpose: Provide cross-cutting logging and helper functions
- Location: `src/utils.py`
- Contains: Colored logging functions (log_info, log_ok, log_error, log_warning), file discovery
- Depends on: Standard library only
- Used by: All modules for consistent logging

## Data Flow

**Main Prediction Flow:**

```
Historical Match Data (data/ARG.csv)
    ↓
[load_data] → Load & Normalize Team Names with Glossary
    ↓
[Sofascore JSON] (src/sofascore_stats.json) → Merge current standings
    ↓
[Fixtures] (partidos.txt) → Parse upcoming matches
    ↓
[build_features] → Elo Ratings Calculation
    ↓ (matches with Elo_Home, Elo_Away, Elo_Diff)
[calculate_poisson_features] → xG, Probabilities (Home/Draw/Away)
    ↓
[compute_trailing_features] → Last 8-match averages (GF/GA/Form)
    ↓
[Feature DataFrame with 24+ columns]
    ↓
[train_validate] → Time-Series CV Split
    ↓ (5 folds, chronological)
[CatBoost/LightGBM] → Trained Model + CV Accuracies
    ↓
[predict_gameweek] → Apply model to fixtures
    ↓
[Predictions + xG + Probabilities]
    ↓
[write_outputs] → Resultados_YYYYMMDD.txt + Feature Importance Chart
```

**State Management:**

- **Immutable Input:** Historical data loaded once at start (data/ARG.csv)
- **Cumulative Elo:** Elo ratings calculated sequentially through match history, stored as dictionary
- **Team History Dictionary:** `team_history[team_name] = [{"date": ..., "gf": ..., "ga": ...}, ...]` - grows during feature computation
- **Feature DataFrame:** Central data structure passed through all pipeline stages with incremental columns added
- **Model Serialization:** Trained model object stored in PipelineResult container for access after training

## Key Abstractions

**Elo Rating System:**
- Purpose: Dynamically track team strength over time with match history
- Examples: `src/stats_engine.py` functions `update_elo()`, `expected_result()`
- Pattern: Sequential update pattern - each match produces new Elo pair based on result
- Formula: `E_new = E_old + K_FACTOR * (Actual_Score - Expected_Score)`
- HOME_ADVANTAGE = 65 points added to home team before calculation

**Poisson Goal Distribution:**
- Purpose: Model goal scoring as a random process to derive outcome probabilities
- Examples: `calculate_expected_goals()`, `calculate_outcome_probabilities()`, `poisson_probability()`
- Pattern: xG calculation (attack/defense balanced) → Poisson PMF for each score → Grid multiplication → Marginalize to Win/Draw/Away
- Calibration: Draw probability multiplied by 0.85 to reduce prediction bias toward draws

**Trailing Features:**
- Purpose: Capture recent team form without requiring match-by-match feature generation
- Examples: `get_team_trailing_stats()`, `compute_trailing_features()`
- Pattern: Chronological iteration through matches, maintaining per-team history window (default: last 8 matches)
- Computes: avg_gf, avg_ga, avg_gd, form (points per game), matches count

**Glossary-Based Normalization:**
- Purpose: Handle inconsistent team name formats across data sources
- Examples: Glossary.txt mappings ("BOCA" → "BOCA JUNIORS")
- Pattern: Upper-case normalization → Glossary lookup → Character cleanup (accents, spaces, dashes)
- Applied to: Historical data, fixtures, Sofascore standings

## Entry Points

**`main.py` - Primary Orchestration:**
- Location: `C:\Scripts\ML_Predictor2026_V2\main.py`
- Triggers: Direct Python execution, PowerShell wrapper (run_model.ps1), CI/automation
- Responsibilities: Calls `run_pipeline()` from src/pipeline.py, displays summary statistics
- Output: Returns (model, elo_ratings, features) tuple for potential further use

**`src/pipeline.py` :: `run_pipeline()` - Pipeline Controller:**
- Location: `C:\Scripts\ML_Predictor2026_V2\src\pipeline.py`
- Triggers: Called from main.py
- Responsibilities: Orchestrates 5-stage pipeline (load_data → build_features → train_validate → predict_fixtures → write_outputs)
- Exception Handling: Wraps entire pipeline in try/except, logs errors but allows exceptions to propagate

**Scraper Entry Points:**
- `scrape_stats_enhanced.py` - FBref web scraper (Selenium)
- `scrape_footystats.py` - FootyStats scraper (Playwright)
- `scrape_sofascore_apify.py` - Sofascore standings (Apify API)
- `scrape_tyc.py` - TyC Sports fixture scraper
- All write to `src/*.csv` or `src/*.json` for consumption by pipeline

**PowerShell Entry Point:**
- `run_model.ps1` - Interactive menu wrapper with prerequisite checks

## Error Handling

**Strategy:** Fail-fast with informative logging; exceptions propagate for visibility

**Patterns:**

- **Data Loading Errors:** Caught and logged with FileNotFoundError details; fixtures marked optional (empty DataFrame if missing)
- **Glossary/Sofascore Loading:** Warnings logged if files missing, functions return empty dict/glossary, pipeline continues
- **Normalization Errors:** pd.isna() checks; empty strings for missing/invalid names
- **Type Safety:** Explicit .fillna() calls before math operations; DEFAULT_EXPECTED_GOALS fallback for missing stats
- **Bounds Checking:** xG clamped to [XG_MIN=0.3, XG_MAX=2.5]; predicted goals clamped to [0, MAX_PREDICTED_GOALS=6]
- **NaN Handling in Features:** Features dropped from training set if contain NaN: `df[FEATURE_COLUMNS].dropna()`

**Recovery Approaches:**
- Missing historical data: Pipeline fails (ARG.csv required)
- Missing fixtures: Prediction stage skipped, model still trained
- Missing Sofascore data: Uses Elo only for predictions
- Missing trailing stats: Uses df_mean (average across training set) as fallback

## Cross-Cutting Concerns

**Logging:**
- Framework: Console logging via custom functions in `src/utils.py`
- Pattern: `log_info()` for steps, `log_ok()` for completion, `log_error()` for failures, `log_warning()` for recoverable issues
- Output: `[INFO]`, `[OK]`, `[ERROR]`, `[WARNING]` prefixed lines to stdout

**Validation:**
- Configuration validation: `src/config.py` validates MODEL_TYPE is "lightgbm" or "catboost", defaults to "catboost"
- Data validation: dropna() calls ensure feature completeness before model training
- Output validation: Probability sums checked to ~1.0 in tests; xG values bounded

**Authentication & Configuration:**
- Environment variable: `ML_PREDICTOR_MODEL` for model selection (default: catboost)
- Apify authentication: Handled within `scrape_sofascore_apify.py` via .env
- No hardcoded secrets; glossary and static data in versioned files

**Date/Time Handling:**
- Fixtures parsed from `partidos.txt` (no inherent date, treated as future matches)
- Historical data sorted by Date column (dayfirst=True for DD/MM/YYYY)
- Output filenames: `Resultados_YYYYMMDD.txt` generated from datetime.now()

---

*Architecture analysis: 2025-03-20*
