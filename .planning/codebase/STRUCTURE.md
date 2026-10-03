# Codebase Structure

**Analysis Date:** 2025-03-20

## Directory Layout

```
ML_Predictor2026_V2/
├── .planning/                           # GSD documentation output
│   └── codebase/                        # Architecture/structure docs
├── .venv/                               # Python virtual environment
├── data/
│   └── ARG.csv                          # Historical match data (28+ seasons)
├── src/                                 # Core library package
│   ├── __init__.py                      # Package marker
│   ├── config.py                        # Constants and hyperparameters
│   ├── data_processing.py               # Data loading, normalization, parsing
│   ├── features.py                      # Feature engineering (Elo, trailing stats)
│   ├── model_engine.py                  # ML model creation and prediction
│   ├── stats_engine.py                  # Statistical calculations (Elo, Poisson)
│   ├── utils.py                         # Logging and utilities
│   ├── sofascore_stats.json             # Scraped team standings (generated)
│   └── [*.csv]                          # Generated scraper output (FBref, FootyStats)
├── tests/
│   ├── __init__.py
│   └── test_main.py                     # Comprehensive unit tests (359 lines)
├── Glossary.txt                         # Team name mappings (ARG teams)
├── main.py                              # Pipeline orchestration entry point
├── requirements.txt                     # Python dependencies (pandas, catboost, etc.)
├── run_model.ps1                        # PowerShell menu wrapper (211 lines)
├── scrape_footystats.py                 # FootyStats Playwright scraper
├── scrape_sofascore.py                  # Sofascore CDP connection scraper
├── scrape_sofascore_apify.py            # Sofascore Apify API scraper
├── scrape_stats_enhanced.py             # FBref Selenium scraper
├── scrape_stats_manual.py               # Manual browser CDP scraper
├── scrape_tyc.py                        # TyC Sports fixture scraper
├── parse_reporte_pdfs.py                # PDF report parser for historical data
├── convert_results.py                   # Utility to convert results format
├── update_arg_csv.py                    # Update historical data from web
├── partidos.txt                         # Fixtures file (generated, cleaned)
├── Resultados_YYYYMMDD.txt              # Predictions output (generated)
├── feature_importance_YYYYMMDD.png      # Feature importance chart (generated)
├── ML_PredictorV2.code-workspace        # VS Code workspace config
└── Readme.md                            # Project documentation
```

## Directory Purposes

**`.planning/codebase/`:**
- Purpose: GSD-generated architecture and structure documentation
- Contains: ARCHITECTURE.md, STRUCTURE.md (this file), CONVENTIONS.md, TESTING.md, CONCERNS.md
- Key files: None (documentation output only)

**`data/`:**
- Purpose: Input data storage (historical matches)
- Contains: CSV files from football-data.co.uk
- Key files: `ARG.csv` (28+ seasons Liga Profesional Argentina match data)

**`src/`:**
- Purpose: Core library code - all reusable modules and calculations
- Contains: Statistical engines, feature builders, ML models, utilities
- Key files: `pipeline.py` (orchestrates execution), `config.py` (all constants), `stats_engine.py` (Elo/Poisson)
- Generated artifacts: `sofascore_stats.json`, `fbref_*.csv`, `footystats_*.csv`

**`tests/`:**
- Purpose: Test suite for core functionality
- Contains: Unit tests for normalization, Elo, Poisson, features
- Key files: `test_main.py` (359 lines, 50+ test functions)

## Key File Locations

**Entry Points:**
- `main.py`: Primary orchestration - calls `src/pipeline.py :: run_pipeline()`
- `run_model.ps1`: PowerShell menu for invoking all scripts
- `scrape_*.py`: Individual data collection scripts (5 variants for different sources)

**Configuration:**
- `src/config.py`: Centralized constants (Elo params, Poisson params, feature columns, model hyperparameters)
- `Glossary.txt`: Team name mappings (one mapping per line: "SOURCE -> TARGET")
- `requirements.txt`: Python dependencies with versions
- `.env`: Environment variables (secrets, not in repo, only .env.example exists)

**Core Logic:**
- `src/stats_engine.py`: All mathematical calculations (Elo, Poisson, expected goals)
- `src/features.py`: Trailing statistics and feature aggregation
- `src/model_engine.py`: Model instantiation, prediction logic
- `src/data_processing.py`: Data loading, normalization, parsing fixtures/glossary

**Testing:**
- `tests/test_main.py`: 50+ unit tests covering Elo, Poisson, normalization, trailing stats, integration
- Run with: `pytest tests/test_main.py` or `pytest tests/test_main.py -v`

## Naming Conventions

**Files:**
- Entry scripts: `scrape_*.py` (scrapers), `parse_*.py` (parsers), `convert_*.py` (converters)
- Core modules: Lowercase with underscores (`data_processing.py`, `model_engine.py`)
- Test files: `test_*.py` (pytest discovery pattern)
- Output predictions: `Resultados_YYYYMMDD.txt` (date-stamped)
- Generated charts: `feature_importance_YYYYMMDD.png` (date-stamped)
- CSV fixtures: `Resultados_YYYYMMDD.csv` (alternative simple format)

**Directories:**
- Source package: `src/` (lowercase, lowercase modules inside)
- Test package: `tests/` (lowercase)
- Data: `data/` (lowercase)
- Output: Root level (no subdirectory by default)

## Where to Add New Code

**New Feature Engineering Function:**
- Primary code: `src/features.py`
- Pattern: Add function that accepts a DataFrame/dict and returns computed feature(s)
- Integration: Call from `build_features()` in `src/pipeline.py`, add column to `FEATURE_COLUMNS`
- Tests: Add test function to `tests/test_main.py`

**New Statistical Calculation:**
- Primary code: `src/stats_engine.py`
- Pattern: Pure functions with no side effects; accept parameters, return results
- Integration: Import and call from feature or model layers
- Tests: Unit test in `tests/test_main.py`

**New Data Source Integration:**
- Primary code: New `scrape_*.py` script at root level
- Pattern: Accept command-line args, output to `src/` directory (JSON or CSV)
- Loading: Add function to `src/data_processing.py`, call from `load_data()` in `src/pipeline.py`
- Tests: Integration test to verify format

**New Model Variant:**
- Primary code: Modify `src/model_engine.py :: create_model()` 
- Configuration: Add hyperparameters to `MODEL_PARAMS` in `src/config.py`
- Selection: Add option to `MODEL_TYPE` env var handling in `src/config.py`
- Testing: Ensure pipeline still completes with new model

**Utility Function (Cross-Module):**
- Primary code: `src/utils.py` (if logging/generic), or specific module if domain-specific
- Pattern: Keep functions small and testable
- Tests: Add to `tests/test_main.py`

## Special Directories

**`src/` (Generated Artifacts):**
- Purpose: Storage for scraped data outputs
- Generated: Yes (by scraper scripts)
- Committed: Partial (.json files committed for Sofascore; .csv files git-ignored)
- Pattern: `{source}_{field}_{date}_{page}.csv` for paginated scrapers, `.json` for API responses
- Cleanup: Old files can be deleted; pipeline uses latest files via glob patterns

**`tests/`:**
- Purpose: Test suite for core functionality
- Generated: No (hand-written)
- Committed: Yes
- Coverage: Unit tests for all statistical functions, feature engineering, normalization
- Run: `pytest tests/test_main.py` (no special configuration)

**Root Level Outputs:**
- Purpose: Final predictions and reports
- Generated: Yes (by `write_outputs()` in pipeline)
- Committed: No (.gitignore includes Resultados_*.txt, *.png)
- Pattern: `Resultados_YYYYMMDD.txt`, `Resultados_Simple_YYYYMMDD.txt`, `feature_importance_YYYYMMDD.png`

## Data File Formats

**`data/ARG.csv` - Historical Match Data:**
- Source: football-data.co.uk
- Format: CSV with columns: Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR, ... (30+ columns including odds)
- Usage: `pd.read_csv("data/ARG.csv")` in `load_data()`
- Key columns used: Date, Home (normalized), Away (normalized), Res (encoded to 0/1/2)

**`partidos.txt` - Fixtures:**
- Format: Text file with lines like "TEAM_A - TEAM_B" or "TEAM_A 1-0 TEAM_B"
- Source: Manually created or scraped from TyC Sports
- Usage: `parse_fixtures()` in `data_processing.py`
- Output from: `scrape_tyc.py`

**`Glossary.txt` - Team Name Mappings:**
- Format: Text file, one mapping per line: "SOURCE -> TARGET" or "SOURCE = TARGET"
- Delimiter: Supports "->", "=", ":" for flexibility
- Usage: `load_glossary()` applies to all data sources for consistency
- Example lines:
  ```
  BOCA -> BOCA JUNIORS
  RIVER -> RIVER PLATE
  SAN LORENZO -> SAN LORENZO
  ```

**`src/sofascore_stats.json` - Current Standings:**
- Format: JSON with team standings array
- Source: `scrape_sofascore_apify.py` or manual scraper
- Usage: `load_sofascore_data()` extracts position, points, goals_for, goals_against
- Structure: `{"teams": [{"name": "...", "position": ..., "points": ..., ...}, ...]}`

**`src/*.csv` - Scraper Outputs:**
- Format: CSV with team statistics from FBref, FootyStats, etc.
- Generated: By respective scrapers (enhanced, manual, footystats variants)
- Pattern: Filename indicates source and date: `fbref_stats_advanced_20260314_14.csv`
- Usage: Not directly in pipeline (data merged into ARG.csv or used for feature engineering)

**`Resultados_YYYYMMDD.txt` - Predictions Output:**
- Format: Human-readable text with match predictions
- Generated: By `write_outputs()` in pipeline
- Contents: Team matchups, predicted scores, xG values, outcome probabilities
- Example:
  ```
  ============================================================
    PREDICCIONES - LIGA PROFESIONAL ARGENTINA
  ============================================================
  BOCA JUNIORS - RIVER PLATE
  Resultado: 2-1 (Home Win)
  xG: 1.45 - 0.78
  ...
  ```

## Dependency Graph (Module Imports)

```
main.py
  └─> src/pipeline.py
      ├─> src/config.py (constants only)
      ├─> src/utils.py (logging)
      ├─> src/data_processing.py
      │   ├─> src/utils.py
      │   └─> src/config.py (RESULT_ENCODING)
      ├─> src/stats_engine.py
      │   ├─> src/config.py (all constants)
      │   └─> scipy.stats.poisson
      ├─> src/features.py
      │   ├─> src/utils.py
      │   └─> numpy/pandas
      └─> src/model_engine.py
          ├─> src/config.py (all constants)
          ├─> src/stats_engine.py (calculate_poisson_features)
          ├─> src/features.py (get_all_teams_latest_stats)
          └─> catboost/lightgbm

scrape_*.py scripts
  └─> src/data_processing.py (normalize_team_name, load_glossary)
      └─> src/utils.py (logging)

tests/test_main.py
  ├─> src/data_processing.py
  ├─> src/stats_engine.py
  ├─> src/features.py
  └─> src/config.py
```

## Configuration and Secrets

**Versioned Configuration:**
- `src/config.py`: All hyperparameters (Elo K_FACTOR=30, Poisson BASE_GOAL_RATE=1.89, etc.)
- `requirements.txt`: Dependency versions
- `.env.example`: Template for required env vars (not read by default)

**Environment Variables:**
- `ML_PREDICTOR_MODEL`: "catboost" or "lightgbm" (default: catboost)
- Apify API key (if using `scrape_sofascore_apify.py`): Set in .env or shell environment
- Chrome debugging port: 9222 (for CDP-based scrapers)

**Secrets Location:**
- `.env` file (project root, git-ignored)
- NOT committed to repo
- Only Apify API credentials needed for some scraper modes

## Build and Run Workflows

**Standard Weekly Prediction:**
```
1. Run scraper (choose one):
   - python scrape_stats_enhanced.py     # Full FBref scrape
   - python scrape_stats_manual.py       # Manual browser with CDP
2. Update fixtures:
   - python scrape_tyc.py
3. Generate predictions:
   - python main.py
4. Results written to: Resultados_YYYYMMDD.txt
```

**Via PowerShell Menu:**
```
.\run_model.ps1 -Option 7  # Run main prediction only
.\run_model.ps1 -Option 8  # Run all data scrapers + prediction
./run_model.ps1            # Interactive menu
```

**Testing:**
```
pytest tests/test_main.py              # Run all tests
pytest tests/test_main.py -v           # Verbose output
pytest tests/test_main.py::test_normalize_team_name_basic  # Single test
```

---

*Structure analysis: 2025-03-20*
