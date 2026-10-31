# ML_Predictor2026_V2 — Architecture

<!-- GSD Configuration -->
<!-- VERIFY: Project structure verified against live repository -->

## Overview
Football match prediction pipeline for Liga Profesional Argentina (2 championships/year). Combines Poisson expectation modeling with CatBoost/LightGBM gradient boosting, dynamic Elo ratings, and market-probability calibration.

## Primary Type
`generic` — Python CLI/data-science project (not monorepo, no web API routes, no deploy config, not open-source licensed).

## Component Graph

```
data/ARG.csv  +  partidos.txt  +  Glossary.txt
       |             |               |
       v             v               v
  +---------+   +----------+   +-------------+
  | src/    |   | scrape_  |   | sources/    |
  | pipeline|   | _tyc.py  |   | fbref/footy|
  +----+----+   +----+-----+   +------+------+
       |             |                |
       v             v                v
  +------------------------------+
  |  Feature engineering (src/features.py, src/dc_features.py, batched_features.py) |
  |    → Elo (stats_engine), xG (Poisson), trailing-8 (exponential decay)           |
  +-----------------------+------------------------------+
                          |
              +-----------+-----------+
              |                       |
        +-----v-----+           +-----v-----+
        | CatBoost  |           | Poisson   |
        | (model_   |           | cali-     |
        |  engine)  |           | bration   |
        +-----+-----+           +-----+-----+
              |                       |
              v                       v
         +---------------------------+
         | _calculate_hybrid_goals() |
         |  (floor(xG) + ML adjust) |
         +------------+--------------+
                      |
               +------v------+
               | Predictions |
               | Resultados_*|
               +-------------+
```

## Key Source Directories

| Path | Contents | Notes |
|---|---|---|
| `src/` | 23 Python modules (pipeline, model_engine, stats_engine, features, validation) | All hyperparameters in `src/config.py` |
| `tests/` | 9 test files (~131+ passing per guidelines) | `test_golden_math.py`, `test_main.py`, `test_pipeline_integration.py`, `test_scraper_utils.py`, etc. |
| `data/` | `ARG.csv`, `sofascore_stats.json` | Historical matches + scraped standings |
| `.opencode/` | GSD v1.42.3 (59 consolidated commands) | Updated from v1.26.0 |

## Verification Notes
- `docs/` directory did not exist before generation (flat structure detected).
- `Readme.md` exists at root with GSD marker (line 148); preserved during update.
- No `package.json`, `Dockerfile`, or deploy config found.
- `tests/` present → yes to test-queue doc.
- `.github/workflows/ci.yml` exists (CI), not a deployment pipeline.

## External Dependencies (from requirements.txt)
- `catboost`, `scipy`, `numpy`, `pandas`, `requests` (scrapers), `playwright` (FBref/FootyStats CDP)
- All pinned in `.venv/` (local, not committed).
