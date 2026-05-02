# PROJECT_STATUS.md

**Last Updated:** 2026-05-02

## Current State

- **Season:** Liga Profesional Argentina — Apertura 2026, Fecha 9 (last regular round)
- **Next:** Playoffs (structure TBD — Argentine football schedules are flexible)
- **Pipeline:** Operational, producing varied scoreline predictions
- **Tests:** 34/34 passing

## Current Metrics

| Metric | Value |
|--------|-------|
| Model | CatBoost (default) |
| CV Accuracy | ~35% (+/- 6%) |
| Log-Loss (model) | ~1.20 |
| Log-Loss (naive baseline) | 1.077 |
| Log-Loss (bookie baseline) | ~1.005 |
| Features | 24 |
| Training samples | ~6,200 matches |

## Feature Importance (Top 5, Apertura 2026)

1. Away_Elo
2. Elo_Diff
3. Home_Elo
4. Form_Balance
5. Home_Avg_GA

## Core Components

| Component | File | Status |
|-----------|------|--------|
| Pipeline orchestration | `src/pipeline.py` | OK |
| Elo + Poisson math | `src/stats_engine.py` | OK |
| ML model + scorelines | `src/model_engine.py` | OK — uses `floor(xG)` + ML adjustment |
| Trailing stats | `src/features.py` | OK — exponential decay, `Home_GF`/`Away_GF` fallback |
| Data normalization | `src/data_processing.py` | OK |
| Pre-flight validation | `src/validation.py` | OK — includes `[SEASON CHECK]` for new teams |
| Scraper resilience | `src/scraper_utils.py` | OK — `@resilient_scraper`, CAPTCHA detection |
| Auto data update | `src/data_ingestion.py` | OK — `enrich_with_api_stats` is a documented no-op |

## Known Limitations

- **ML accuracy is near-random (~35%)** on a 3-class problem. Poisson component is more reliable for scoreline spread. Treat predictions as informed starting points.
- **Playoffs:** Model was trained on regular season data. Knockout dynamics (leg management, rotation) are not captured. Poisson weight may be more reliable than ML for playoff predictions.
- **`enrich_with_api_stats`** in `data_ingestion.py` is a no-op — API-Football team name fuzzy matching not yet implemented.
- **TyC scraper** requires a current-season URL passed via `--url`. TyC changes HTML structure frequently; manual `Partidos.txt` update is the reliable fallback.

## Recent Changes (May 2026)

### Scoreline Bug Fix
- **Problem:** All scores were 1-1 (14/15 matches)
- **Root cause 1:** `_calculate_hybrid_goals` used `round(xG)` — Liga Profesional xG values (0.8–1.6) all round to 1
- **Root cause 2:** ML adjustment threshold `ml_weight > 0.3` was unreachable (scaled weight always 0.21–0.27)
- **Root cause 3:** `get_all_teams_latest_stats` read `GF`/`GA` as zeros when `Home_GF`/`Away_GF` columns were present instead
- **Fix:** `floor(xG)` as base; `max_prob >= 0.35` direct threshold; `Home_GF`/`Away_GF` fallback in stats lookup

### Glossary Additions
- `Boca -> BOCA JUNIORS`
- `Independiente Rivadavia Mza -> IND RIVADAVIA` (and variants)

### Scraper Fix
- `scrape_tyc.py` hardcoded URL and Fecha 6 team list removed; now accepts `--url` and `--fecha` CLI args

### Other Fixes Applied
- `GF`/`GA` column mapping bug in `pipeline.py` (was assigning `Away_GF` to `GA` via wrong variable)
- `enrich_with_api_stats` stub replaced with explicit no-op log message
- Season-start new-team detection added to `load_data()`
- `BASE_GOAL_RATE` clarified as NaN fallback only (not a scaling factor)
- `calibrate_poisson_params()` added to `stats_engine.py`
- Output filename fallback to date-based when no FECHA number in header
- Model name in summary reads from `type(result.model).__name__`
- Test suite updated: column names fixed (`HomeTeam`/`AwayTeam`), 5 new tests added

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| Poisson Calibration | Run `calibrate_poisson_params()` and tune `POISSON_DRAW_ADJUSTMENT` | Pending |
| Playoff Support | Consider increasing Poisson blend ratio for knockout rounds | Pending |
| `enrich_with_api_stats` | Implement API-Football team name mapping | Pending |
