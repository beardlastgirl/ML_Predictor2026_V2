<!-- GSD Configuration — managed by get-shit-done installer -->
# Instructions for GSD

- Use the get-shit-done skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.
<!-- /GSD Configuration -->

---

# Copilot Instructions: ML_Predictor2026_V2

## Project Overview

ML_Predictor2026_V2 is a football match prediction system for Liga Profesional Argentina that combines:
- **Elo ratings** (dynamic team strength)
- **Poisson distribution** for goal modeling (xG-based outcome probabilities)
- **Gradient boosting** (CatBoost/LightGBM) for calibrated predictions
- **Scraped data** from FBref, FootyStats, TyC Sports, Sofascore, and PDF reports
- **AI-powered PR Management**: Qodo Merge (PR-Agent) for code reviews and PR automation

The system generates weekly predictions in `Resultados_YYYYMMDD.txt` reports.

## Build, Test, and Development Commands

```powershell
# Environment setup (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the complete prediction pipeline
python main.py

# Run via interactive PowerShell menu (recommended for weekly workflow)
.\run_model.ps1

# Run menu non-interactively
.\run_model.ps1 -Option 7   # Main prediction model only
.\run_model.ps1 -Option 8   # All scrapers + prediction

# Run full test suite
python -m pytest tests/test_main.py

# Run a specific test
python -m pytest tests/test_main.py::test_normalize_team_name
python -m pytest tests/test_main.py -k poisson  # Run tests matching 'poisson'
```

## High-Level Architecture

### Data Pipeline

```
[Multiple Sources]
  ├─ FBref (Selenium scraper)
  ├─ FootyStats (Playwright scraper)
  ├─ TyC Sports (BeautifulSoup scraper → partidos.txt)
  ├─ Sofascore (Apify-based → src/sofascore_stats.json)
  ├─ PDF Reports (pdfplumber)
  └─ Historical data (data/ARG.csv)
         ↓
[Normalization via Glossary.txt]
         ↓
[src/pipeline.py] Load + Build Features + Train + Predict
         ↓
[Output: Resultados_YYYYMMDD.txt + feature_importance_*.png]
```

### Core Modules (in `src/`)

| Module | Responsibility | Key Functions |
|--------|-----------------|----------------|
| **pipeline.py** | Orchestration: data load → feature build → train → predict → output | `run_pipeline()`, `load_data()`, `build_features()`, `train_validate()`, `predict_fixtures()`, `write_outputs()` |
| **stats_engine.py** | Elo math, Poisson distribution, Shin odds | `calculate_all_elo_ratings()`, `calculate_poisson_features()`, `calculate_outcome_probabilities()`, `shin_method()` |
| **features.py** | Trailing averages and team form | `compute_trailing_features()` |
| **model_engine.py** | ML model creation and fixture prediction | `create_model()`, `predict_gameweek()` (60/40 ML+Poisson blend) |
| **data_processing.py** | Data loading, team normalization, fixture parsing | `load_glossary()`, `normalize_team_name()`, `parse_fixtures()`, `load_sofascore_data()` |
| **config.py** | Hyperparameters: Elo, Poisson, model selection | Tunable constants (BASE_ELO, BASE_GOAL_RATE, POISSON_DRAW_ADJUSTMENT, etc.) |
| **utils.py** | Logging without ANSI codes | `log_info()`, `log_ok()`, `log_warning()`, `log_error()` |

### Key Data Files

| File | Purpose |
|------|---------|
| `data/ARG.csv` | Historical match results (H/D/A → 2/1/0 encoding) |
| `partidos.txt` | Upcoming fixtures (parsed from TyC Sports) |
| `src/sofascore_stats.json` | Current standings (attack/defense metrics) |
| `Glossary.txt` | Team name canonicalization (TyC ↔ FBref ↔ FootyStats ↔ ARG.csv) |

## Key Conventions

### Naming & Code Style

- **Modules**: `snake_case.py` (e.g., `stats_engine.py`)
- **Functions/variables**: `snake_case` (e.g., `calculate_poisson_features`)
- **Feature columns**: `Title_Case_With_Underscores` (e.g., `Home_Elo`, `Poisson_Draw`)
- **Logging**: Use `src/utils.py` helpers (`log_info`, `log_ok`, `log_warning`, `log_error`) — **NO ANSI color codes** ever
- **Indentation**: 4 spaces (Python standard)

### Critical Data Normalization

**All team names must converge to a single canonical set.** When adding a new data source or updating `Glossary.txt`:
1. Ensure `normalize_team_name()` is called on all ingested team names
2. Test that fixtures merge correctly with `data/ARG.csv`
3. Check `Glossary.txt` for any missing mappings

### Draw Probability Calibration

Draw handling is spread across three locations; tune them together:
1. **Poisson adjustment**: `src/stats_engine.calculate_outcome_probabilities()` uses `POISSON_DRAW_ADJUSTMENT` (default 0.85)
2. **Training weights**: `src/pipeline.train_validate()` down-weights draws via sample weights
3. **Prediction blending**: `src/model_engine.predict_gameweek()` blends ML+Poisson at 60/40

### Result Encoding

Results are encoded as:
- `H` (Home) → `2`
- `D` (Draw) → `1`
- `A` (Away) → `0`

(See `src/config.py` for `RESULT_ENCODING` and `RESULT_DECODING`)

### Time-Series Features

Features are built **chronologically** to avoid data leakage:
- `src/features.py` computes trailing averages from lookback windows (default: last 8 matches)
- Elo ratings are updated in historical order before feature computation
- `src/pipeline.train_validate()` uses `TimeSeriesSplit` for cross-validation

### Environment Variables

```bash
# Optional: Select ML model backend (default: catboost)
ML_PREDICTOR_MODEL=catboost  # or lightgbm

# Optional: Apify token for Sofascore scraping
APIFY_API_TOKEN=your_token_here
```

### Scrapers & Data Input (at repo root)

| Script | Input | Output | Notes |
|--------|-------|--------|-------|
| `scrape_stats_enhanced.py` | FBref | `src/results_*.csv` | Selenium; may hit CAPTCHAs |
| `scrape_stats_manual.py` | FBref/FootyStats | `src/results_*.csv` | Manual browser (CDP); recommended fallback |
| `scrape_footystats.py` | FootyStats | `src/footystats_*.csv` | Playwright; xG and per-game stats |
| `scrape_sofascore_apify.py` | Sofascore | `src/sofascore_stats.json` | Apify API; recommended for standings |
| `scrape_tyc.py` | TyC Sports | `partidos.txt` | BeautifulSoup; fixture/result updates |
| `parse_reporte_pdfs.py` | `Reporte/*.pdf` | Optionally updates `data/ARG.csv` | PDF match results |

### Output Artifacts

- **Predictions**: `Resultados_YYYYMMDD.txt` (match outcomes, scoreline predictions, ML/Poisson probabilities)
- **Feature importance**: `feature_importance_YYYYMMDD.png` (matplotlib bar chart)

## Testing

- **Framework**: pytest
- **Test location**: `tests/test_main.py`
- **Focus areas**: Data normalization, Elo math, Poisson probabilities, trailing feature calculation

Example:
```powershell
# Run all tests
python -m pytest tests/test_main.py -v

# Run only Poisson-related tests
python -m pytest tests/test_main.py -k poisson -v

# Run with coverage report
python -m pytest tests/test_main.py --cov=src --cov-report=html
```

## Commit Guidelines

Use Conventional Commits with scope:
- `feat(stats_engine): add Shin odds method`
- `fix(data_processing): normalize team names for new data source`
- `docs(README): update scraper instructions`
- `chore(config): tune POISSON_DRAW_ADJUSTMENT`

When modifying core logic (Elo, Poisson, feature engineering), include before/after metrics in the PR description.

## Important Files to Know

| File | When to Edit |
|------|--------------|
| `src/config.py` | Tuning Elo parameters, Poisson constants, model hyperparameters |
| `src/stats_engine.py` | Changing xG formula, Poisson calibration, Elo algorithm |
| `src/model_engine.py` | Adjusting ML+Poisson blending ratio, scoreline heuristics |
| `src/pipeline.py` | Adding/removing features, changing training CV strategy |
| `src/data_processing.py` | Adding data source, new team name variants, fixture parsing changes |
| `Glossary.txt` | Mapping new team names across sources |
| `tests/test_main.py` | Adding regression tests for new logic |

## Potential Issues & Gotchas

### "No files match pattern src/results*.csv"
Run a stats scraper first (e.g., `python scrape_stats_enhanced.py`).

### Team names don't merge with historical data
Check and update `Glossary.txt`, then verify `normalize_team_name()` is applied in the ingestion path.

### Draw predictions seem off
Check all three draw calibration locations (see above). Tune `POISSON_DRAW_ADJUSTMENT` and sample weights together.

### Model accuracy drops after scraper updates
Verify features are computed in chronological order (no data leakage). Check that `TimeSeriesSplit` is active in `train_validate()`.

---

*For more details, see CLAUDE.md, AGENTS.md, and DEV_CONTEXT/*
