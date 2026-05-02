# ML_Predictor2026_V2 — System Architecture

## Pipeline Flow

```
Partidos.txt (fixtures)
data/ARG.csv (history)          ─┐
src/sofascore_stats.json         ├─> pipeline.py ─> PrediccionFechaXX.txt
Glossary.txt                    ─┘               ─> feature_importance_*.png

pipeline.py stages:
  load_data()        → normalize teams, validate inputs, [SEASON CHECK]
  build_features()   → Elo ratings, trailing stats, Poisson xG, Shin odds
  train_validate()   → 5-fold time-series CV, CatBoost/LightGBM
  predict_fixtures() → ensemble blend (60% ML + 40% Poisson), scorelines
  write_outputs()    → PrediccionFechaXX.txt, feature importance chart
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `src/config.py` | Single source of truth for all hyperparameters |
| `src/pipeline.py` | Orchestration, data loading, feature assembly, output writing |
| `src/stats_engine.py` | Elo system, Poisson xG, outcome probabilities, Shin method, `calibrate_poisson_params()` |
| `src/model_engine.py` | Model factory, `predict_gameweek()`, `_calculate_hybrid_goals()` |
| `src/features.py` | Exponential-decay trailing stats, `get_all_teams_latest_stats()` |
| `src/data_processing.py` | Team name normalization, glossary, fixture parsing, header mapping |
| `src/data_ingestion.py` | Auto-download ARG.csv from football-data.co.uk |
| `src/validation.py` | Pre-flight validation (glossary, history, fixtures, features) |
| `src/scraper_utils.py` | `@resilient_scraper` decorator, CAPTCHA detection, health monitor |
| `src/map_headers.py` | Canonical header mapping for ARG.csv columns |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `floor(xG)` for scorelines | `round()` collapses Liga Profesional xG values (0.8–1.6) to 1; floor gives spread |
| 60% ML + 40% Poisson blend | ML captures patterns; Poisson provides calibrated baseline |
| `max_prob >= 0.35` ML adjustment threshold | Scaled weight (old approach) never fired; direct probability check works |
| Exponential decay trailing stats | Recent matches weighted more than older ones |
| `Home_GF`/`Away_GF` fallback in `get_all_teams_latest_stats` | `GF`/`GA` columns may not exist in all DataFrames passed to this function |
| `BASE_GOAL_RATE` as NaN fallback only | Not a scaling factor in xG formula; used when team has no trailing stats |
| Season check warning | Promoted/new teams get default Elo (1500) and zero stats; explicit warning prevents silent bad predictions |

## Orchestrator

Claude Code is the single orchestrator. Three specialist roles only:

| Role | Trigger |
|------|---------|
| planner | Ambiguous task spanning 3+ files |
| debugger | Reproducible test failure or scraper breakage |
| code-reviewer | Post-implementation review (read-only) |

State lives in `,ai/state/current.md` (active task) and `,ai/state/decisions.md` (ADRs).

## Directory Layout

```
ML_Predictor2026_V2\
├── main.py                  ← entry point
├── Partidos.txt             ← current fixtures (edit weekly)
├── Glossary.txt             ← team name mappings
├── data\ARG.csv             ← historical match data
├── src\                     ← core source code
├── tests\                   ← pytest suite (34 tests)
├── Reporte\                 ← PDF match reports
├── DEV_CONTEXT\             ← technical documentation
├── .planning\               ← roadmap and requirements
├── ,ai\state\               ← agent state (current task, ADRs)
└── .venv\                   ← Python virtual environment
```
