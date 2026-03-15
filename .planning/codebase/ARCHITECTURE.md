# Architecture

**Analysis Date:** 2026-03-15

## Pattern Overview

**Overall:** Modular Pipeline Architecture

**Key Characteristics:**
- Separation of concerns: scrapers, core engine, utilities
- Pipeline orchestration pattern (`src/pipeline.py`)
- Functional decomposition for math/statistics
- Dataflow: scrape -> normalize -> featurize -> train -> predict -> output

## Layers

**Scrapers Layer:**
- Purpose: Fetch external data from sports websites
- Location: `scrape_*.py` (project root)
- Contains: 6 scraper scripts for different data sources
- Depends on: requests, selenium, playwright, beautifulsoup4
- Used by: Manual execution or `run_model.ps1` menu

**Data Processing Layer:**
- Purpose: Load, normalize, and clean data
- Location: `src/data_processing.py`
- Contains: `load_glossary`, `normalize_team_name`, `load_sofascore_data`, `parse_fixtures`
- Depends on: pandas, json, re
- Used by: `src/pipeline.py`

**Statistics Engine Layer:**
- Purpose: Mathematical implementations (Elo, Poisson)
- Location: `src/stats_engine.py`
- Contains: `calculate_expected_goals`, `calculate_outcome_probabilities`, `update_elo`
- Depends on: scipy.stats.poisson, numpy
- Used by: `src/features.py`, `src/model_engine.py`

**Feature Engineering Layer:**
- Purpose: Create ML features from historical data
- Location: `src/features.py`
- Contains: `compute_trailing_features`, `get_all_teams_latest_stats`
- Depends on: `src/stats_engine`, `src/utils`
- Used by: `src/pipeline.py`

**Model Engine Layer:**
- Purpose: Model creation and prediction logic
- Location: `src/model_engine.py`
- Contains: `create_model`, `predict_gameweek`
- Depends on: catboost, lightgbm, `src/stats_engine`, `src/features`
- Used by: `src/pipeline.py`

**Pipeline Orchestration Layer:**
- Purpose: End-to-end workflow coordination
- Location: `src/pipeline.py`
- Contains: `run_pipeline`, `load_data`, `build_features`, `train_validate`, `predict_fixtures`, `write_outputs`
- Depends on: All other layers
- Used by: `main.py`

**Entry Point Layer:**
- Purpose: Application bootstrap
- Location: `main.py`
- Contains: `main()` function calling `run_pipeline()`
- Depends on: `src.pipeline`, `src.utils`
- Used by: Direct execution or PowerShell menu

## Data Flow

**Training Pipeline:**

1. Load historical data from `data/ARG.csv`
2. Normalize team names using `Glossary.txt`
3. Calculate Elo ratings chronologically (`stats_engine.calculate_all_elo_ratings`)
4. Compute trailing-average features (`features.compute_trailing_features`)
5. Calculate Poisson features for each match (`stats_engine.calculate_poisson_features`)
6. Train model with time-series CV (`pipeline.train_validate`)
7. Generate feature importance chart
8. Save results to `Resultados_{date}.txt`

**Prediction Pipeline:**

1. Load fixtures from `partidos.txt`
2. Load current standings from `src/sofascore_stats.json`
3. Precompute latest team stats from history
4. For each fixture:
   - Lookup Elo ratings
   - Fetch trailing stats (avg_gf, avg_ga, form)
   - Calculate Poisson features (xG, outcome probs)
   - ML model prediction (CatBoost/LightGBM)
   - Ensemble: 60% ML + 40% Poisson probabilities
5. Determine scoreline from xG and prediction
6. Write predictions to output file

**Scraping Workflow:**

1. User runs `run_model.ps1` menu option
2. Selected scraper executes:
   - FBref: Selenium with anti-bot detection
   - FootyStats: Playwright or CDP manual browser
   - Sofascore: Apify API
   - TyC: requests + BeautifulSoup
3. Data saved to `src/` directory
4. Main pipeline uses scraped data for next run

## State Management

**Elo Ratings:**
- Computed fresh each run from historical data
- No persistence between runs
- Stored in memory as dict during pipeline execution

**Model:**
- Trained fresh each run (no model persistence)
- Time-series cross-validation ensures reproducibility

**Scraped Data:**
- Cached in `src/` directory as CSV/JSON files
- Rate limiting: `scrape_stats_manual.py` checks last scrape date

## Key Abstractions

**PipelineResult:**
- Purpose: Container for pipeline execution results
- Location: `src/pipeline.py` (lines 46-58)
- Pattern: Data class with typed attributes
- Examples: `model`, `elo_ratings`, `cv_accuracies`, `fixtures`, `output_file`

**Poisson Features:**
- Purpose: Derived probabilities from goal distributions
- Location: `src/stats_engine.calculate_poisson_features`
- Pattern: Dict return with 9 features
- Examples: `xG_home`, `Poisson_Home_Win`, `Expected_Total_Girls`

**Trailing Stats:**
- Purpose: Form-based features from recent matches
- Location: `src/features.get_team_trailing_stats`
- Pattern: Rolling window aggregation
- Examples: `avg_gf`, `avg_ga`, `form` (points per game)

## Entry Points

**main.py:**
- Location: `C:\Scripts\ML_Predictor2026_V2\main.py`
- Triggers: `python main.py` or PowerShell menu option 7
- Responsibilities: Call `run_pipeline()`, log summary

**run_model.ps1:**
- Location: `C:\Scripts\ML_Predictor2026_V2\run_model.ps1`
- Triggers: `.\run_model.ps1`
- Responsibilities: Interactive menu for all operations

**scrape_*.py scripts:**
- Location: Project root
- Triggers: Individual execution or menu options 1-6
- Responsibilities: Fetch specific data source

## Error Handling

**Strategy:** Fail-fast with informative logging

**Patterns:**
- Try/except blocks in all I/O operations
- Custom logging utilities (`log_error`, `log_warning`)
- Graceful degradation: missing files logged but continue
- Pipeline exceptions re-raised after logging

## Cross-Cutting Concerns

**Logging:**
- Custom utilities in `src/utils.py`
- Plain ASCII prefixes: `[INFO]`, `[OK]`, `[ERROR]`, `[WARNING]`
- No ANSI colors (per project guidelines)

**Validation:**
- Team name normalization via `Glossary.txt`
- Data type coercion with `pd.to_numeric(errors="coerce")`
- NaN handling with `.fillna()` and `.dropna()`

**Authentication:**
- Apify token via env var or embedded default
- No OAuth or session management

---

*Architecture analysis: 2026-03-15*
