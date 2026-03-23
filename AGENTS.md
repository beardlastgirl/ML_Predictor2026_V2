# Repository Guidelines

## Project Structure & Module Organization

- **Core pipeline code** lives in `src/` (Python package). The main orchestration entry point is `main.py`, which delegates to `src/pipeline.py`.
- **Data inputs**:
  - `data/ARG.csv` - historical matches used for training.
  - `partidos.txt` - upcoming fixtures (and sometimes results) parsed into a fixtures DataFrame.
  - `src/sofascore_stats.json` - Sofascore standings used as additional features.
  - `Glossary.txt` - canonical team-name mapping used to normalize all sources.
- **Scrapers / ingestion scripts** are in the repository root (for FBref, TyC, Sofascore/Apify, PDFs). A small HTTP API lives in `scripts/`.
- **Tests** are in `tests/` and focus on Elo/Poisson math and feature engineering.

## Build, Test, and Development Commands

```powershell
# Create + activate venv (Windows)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the end-to-end prediction pipeline
python main.py

# Menu wrapper to run scrapers/pipeline (interactive)
.\run_model.ps1

# Menu wrapper (non-interactive)
.\run_model.ps1 -Option 7   # run main prediction model
.\run_model.ps1 -Option 8   # run all scrapers + prediction

# Run tests
python -m pytest tests/test_main.py
```

## Coding Style & Naming Conventions

- **Language**: Python.
- **Logging**: use the plain ASCII helpers in `src/utils.py` (`log_info`, `log_ok`, `log_warning`, `log_error`). This codebase consistently avoids ANSI color codes.
- **Naming**:
  - Modules use `snake_case.py` (e.g., `stats_engine.py`, `data_processing.py`).
  - Functions/variables use `snake_case` (e.g., `calculate_poisson_features`, `normalize_team_name`).
  - Feature columns are `Title_Case_With_Underscores` (e.g., `Home_Elo`, `Poisson_Draw`).
- **Formatting**: no formatter config is present in-repo (no `pyproject.toml` found). Keep changes consistent with existing files (4-space indentation).

## Testing Guidelines

- **Framework**: `pytest` (declared in `requirements.txt`).
- **Test files**: `tests/test_main.py`.
- **Running tests**: `python -m pytest tests/test_main.py`.

## Commit & Pull Request Guidelines

- **Commit format** (observed in git history): Conventional Commits-style prefixes such as `docs: ...`, `chore: ...`, `feat(scope): ...` (e.g., `feat(01-01): implement Shin Method in stats_engine.py`).
- **PR expectations**: Keep PRs small, include a clear description of data/feature changes, and attach before/after metrics when modifying model behavior.
- **AI-powered PR Review**: This repository uses **Qodo Merge (PR-Agent)** for automated PR analysis, summaries, and suggestions. Tag `@CodiumAI-Agent /review` or use the GitHub Action flow for automated feedback.

---

# Repository Tour

## 🎯 What This Repository Does

ML_Predictor2026_V2 is a Python pipeline that predicts Liga Profesional Argentina match outcomes and scorelines by combining Elo ratings, trailing-form features, and Poisson goal modeling, then learning a calibrated outcome classifier with CatBoost/LightGBM.

**Key responsibilities:**
- Build chronological Elo + trailing performance features from `data/ARG.csv`.
- Derive xG and H/D/A probabilities via Poisson and add them as model features.
- Predict upcoming fixtures from `partidos.txt` and write a `Resultados_YYYYMMDD.txt` report.

---

## 🏗️ Architecture Overview

The repository is a single-machine, file-driven pipeline. Data is scraped/updated into local files and then consumed by the training/prediction pipeline.

### System Context

```text
[Scrapers / PDFs / Manual inputs]
   |  (write CSV/JSON/TXT)
   v
[Local files: data/ARG.csv, partidos.txt, src/sofascore_stats.json]
   |
   v
[main.py] -> [src/pipeline.py] -> trains model + predicts fixtures -> Resultados_*.txt (+ feature_importance_*.png)
```

### Key Components

- **Orchestrator**: `main.py`
  - Calls `src.pipeline.run_pipeline()` and prints a short summary.
- **Pipeline service**: `src/pipeline.py`
  - `load_data()` loads glossary, sofascore JSON, historical matches, and fixtures.
  - `build_features()` computes Shin odds probabilities (if odds columns exist), Elo, trailing stats, and Poisson-derived features.
  - `train_validate()` fits CatBoost/LightGBM with `TimeSeriesSplit` CV and sample weights that down-weight draws.
  - `predict_fixtures()` delegates to `src.model_engine.predict_gameweek()`.
  - `write_outputs()` writes `Resultados_YYYYMMDD.txt` and saves `feature_importance_YYYYMMDD.png`.
- **Math engines**:
  - `src/stats_engine.py` implements Elo updates, expected goals, Poisson outcome probabilities, and the Shin method (`shin_method`).
  - `src/features.py` computes trailing averages and recent form for each team chronologically.
- **Model layer**: `src/model_engine.py`
  - `create_model()` builds CatBoost/LightGBM using `src/config.py` hyperparameters.
  - `predict_gameweek()` builds fixture features, blends ML and Poisson probabilities (60/40), and generates scorelines.
- **Normalization / IO**: `src/data_processing.py`
  - `load_glossary()` and `normalize_team_name()` ensure consistent team naming.
  - `load_sofascore_data()` supports multiple Sofascore JSON formats.
  - `clean_partidos_file()` and `parse_fixtures()` ingest `partidos.txt`.
- **HTTP API (optional)**: `scripts/api_server.py` and `scripts/api_predict.py`
  - Reads latest `Resultados_*.txt` and exposes/prints JSON for fixtures and predictions.

### Data Flow

1. Update local inputs (scrape or manually edit): `data/ARG.csv`, `partidos.txt`, `src/sofascore_stats.json`, `Glossary.txt`.
2. Run `python main.py` (or `run_model.ps1` option 7/8).
3. `src/pipeline.load_data()` normalizes teams and encodes results (`H/D/A` -> `2/1/0`).
4. `src/pipeline.build_features()` computes Elo (`calculate_all_elo_ratings`), trailing features (`compute_trailing_features`), Shin probabilities (if odds exist), and Poisson features (`calculate_poisson_features`).
5. `src/pipeline.train_validate()` performs time-series CV, then trains the final model.
6. `src/model_engine.predict_gameweek()` builds fixture features, blends ML+Poisson probabilities, and chooses scorelines.
7. `src/pipeline.write_outputs()` writes the results report and a feature importance PNG.

---

## 📁 Project Structure [Partial Directory Tree]

```text
ML_Predictor2026_V2/
├── main.py                         # Entry point; runs src.pipeline.run_pipeline()
├── src/                            # Core package (pipeline + engines)
│   ├── config.py                   # Elo/Poisson/model parameters; env var ML_PREDICTOR_MODEL
│   ├── pipeline.py                 # Orchestrates load -> feature -> train -> predict -> write outputs
│   ├── stats_engine.py             # Elo + Poisson math; Shin method
│   ├── features.py                 # Trailing averages + form features
│   ├── model_engine.py             # Model factory + fixture prediction + probability blending
│   ├── data_processing.py          # Glossary + team normalization + fixtures + sofascore parsing
│   └── utils.py                    # Plain ASCII logging + file helpers
├── data/
│   └── ARG.csv                     # Historical match dataset used for training
├── tests/
│   └── test_main.py                # pytest suite for normalization, Elo, Poisson, trailing features
├── scripts/
│   ├── api_server.py               # Minimal HTTPServer exposing JSON endpoints
│   └── api_predict.py              # CLI that prints JSON predictions
├── DEV_CONTEXT/                    # Project notes, status, roadmap, and system knowledge
├── run_model.ps1                   # Menu runner for scrapers and pipeline
├── setup_venv.ps1                  # Creates venv and installs requirements
├── scrape_stats_enhanced.py        # FBref scraper (Selenium)
├── scrape_stats_manual.py          # CDP manual-browser scraper (FBref/FootyStats)
├── scrape_footystats.py            # FootyStats scraper (Playwright)
├── scrape_sofascore_apify.py       # Sofascore scraper using Apify API
├── scrape_tyc.py                   # TyC Sports scraper (writes partidos.txt)
└── parse_reporte_pdfs.py           # Parse PDF reports under Reporte/ and optionally update ARG.csv
```

### Key Files to Know

| File | Purpose | When You'd Touch It |
|------|---------|---------------------|
| `main.py` | Small entry point for the end-to-end pipeline | Changing what runs by default / scripting runs |
| `src/pipeline.py` | Orchestration of data loading, feature building, training, and outputs | Adding/removing features, changing CV/training, output format |
| `src/stats_engine.py` | Elo + Poisson implementation (and Shin odds method) | Tuning xG formula, Poisson calibration, Elo parameters |
| `src/model_engine.py` | Fixture prediction, probability blending, scoreline generation | Adjusting calibration / scoreline heuristics |
| `src/data_processing.py` | Input normalization (Glossary, fixtures, Sofascore JSON) | When a data source changes format / new team name variants |
| `src/config.py` | Central hyperparameters and thresholds | Tuning model choice/params and Poisson/Elo constants |
| `run_model.ps1` | Menu wrapper for common tasks | Running locally; adding new menu entries |
| `.env.example` | Documents required env vars (Apify token, model choice) | Setting up a new machine |
| `tests/test_main.py` | Regression tests for the math and feature logic | Extending coverage after changing core logic |

---

## 🔧 Technology Stack

### Core Technologies
- **Language:** Python (minimum version noted in `Readme.md`: 3.8+)
- **Data/Math:** pandas, numpy, scipy (`requirements.txt`)
- **ML:** CatBoost and LightGBM (`requirements.txt`), with scikit-learn for metrics and `TimeSeriesSplit`

### Key Libraries
- **scipy.stats.poisson** - Poisson pmf for goal distributions (`src/stats_engine.py`).
- **catboost / lightgbm** - Gradient boosting classifier backend (`src/model_engine.py`).
- **matplotlib** - Feature importance bar chart output (`src/pipeline.py`).

### Development Tools
- **pytest** - test runner (`tests/test_main.py`, `requirements.txt`).

---

## 🌐 External Dependencies

### Required Services
- **Apify (optional but supported)** - used by `scrape_sofascore_apify.py` to fetch Sofascore standings via the `apify-client`.

### Data Sources (via scraping/manual update)
- **FBref** - team stats tables (`scrape_stats_enhanced.py`, `scrape_stats_manual.py`).
- **FootyStats** - advanced metrics tables (`scrape_footystats.py`, also supported by `scrape_stats_manual.py`).
- **TyC Sports** - fixtures/results (`scrape_tyc.py`, writes `partidos.txt`).
- **PDF reports** - parsed from `Reporte/` (`parse_reporte_pdfs.py`).

---

### Environment Variables  [Optional]

```bash
# Apify API token used by scrape_sofascore_apify.py
APIFY_API_TOKEN=...

# Model selection read by src/config.py (default: catboost)
ML_PREDICTOR_MODEL=catboost
```

---

## 🚨 Things to Be Careful About

### Data normalization is critical
All sources must converge on the same canonical team names. When fixtures fail to merge or a team appears missing, update `Glossary.txt` and ensure `normalize_team_name()` is applied for that ingestion path.

### Draw calibration exists in multiple places
- Poisson draw probability is adjusted in `src/stats_engine.calculate_outcome_probabilities()` via `POISSON_DRAW_ADJUSTMENT`.
- Training uses sample weights that down-weight draws in `src/pipeline.train_validate()`.
- Fixture prediction blends ML+Poisson probabilities in `src/model_engine.predict_gameweek()`.

If you tune draw behavior, check all three.

---

*Update to last commit: a53f7f001cd40192a0cfb90c11fc2982325684e9*
*Updated at: 2026-03-20*
