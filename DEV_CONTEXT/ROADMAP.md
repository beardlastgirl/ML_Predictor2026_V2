# ROADMAP.md

**Last Updated:** 2026-05-02

## Completed

- [x] Modular architecture (`src/` package)
- [x] Poisson distribution goal modeling
- [x] CatBoost/LightGBM with time-series CV
- [x] Shin method odds extraction
- [x] Sofascore Apify integration
- [x] FootyStats Playwright scraper
- [x] Pre-flight data validation (`src/validation.py`)
- [x] Scraper resilience (`@resilient_scraper`, CAPTCHA detection)
- [x] Baseline comparison (naive + bookie log-loss in output)
- [x] Scoreline bug fix — `floor(xG)` + ML directional adjustment
- [x] Season-start new-team detection (`[SEASON CHECK]` warning)
- [x] `calibrate_poisson_params()` utility
- [x] `scrape_tyc.py` — removed hardcoded season data, `--url`/`--fecha` args
- [x] 34 tests passing

## Pending

### High Value
- [x] **Run Poisson calibration** — calibrated 2026-05-02 against 6,171 matches
  - `POISSON_DRAW_ADJUSTMENT = 1.11` (was 0.85 — wrong direction)
  - `HOME_ADVANTAGE_BOOST = 0.02` (was 0.08 — double-counting home advantage)
  - Result: predicted home=43.0%, draw=30.3%, away=26.6% vs actual 43.1/30.3/26.6
- [x] **`enrich_with_api_stats`** — implemented API-Football team name fuzzy matching
  - Curated map for 10 known mismatches + fuzzy fallback (cutoff=0.75)
  - Adds `HxG`, `AxG`, `HPoss`, `APoss` columns to ARG.csv
  - Free plan limitation: only covers seasons up to 2024; 2025/2026 data unavailable
  - Rate limit: 100 req/day; 0.5s delay between requests; stops at 80 to leave buffer

### Medium Value
- [ ] **Playoff mode** — option to increase Poisson blend ratio (e.g. 0.5/0.5) for knockout rounds where ML signal is weaker
- [ ] **Accuracy tracking** — SQLite log of predictions vs actual results per round
- [ ] **Hyperparameter tuning** — grid search on CatBoost depth/iterations/learning_rate

### Low Value / Future
- [ ] Ensemble LightGBM + CatBoost voting
- [ ] Copa Libertadores / Copa Argentina fixture support
- [ ] Web dashboard for predictions
