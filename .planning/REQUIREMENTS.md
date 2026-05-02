# Requirements

**Last Updated:** 2026-05-02

## Delivered

- ✅ Modular architecture with clear separation of concerns
- ✅ Poisson distribution goal modeling
- ✅ CatBoost/LightGBM with time-series cross-validation
- ✅ Betting odds integration (Shin method features)
- ✅ Baseline comparison (naive + bookie log-loss)
- ✅ Pre-flight data validation
- ✅ Scraper resilience (retry, CAPTCHA detection)
- ✅ Season-start new-team detection
- ✅ Realistic scoreline generation (floor(xG) + ML adjustment)

## Pending

- [ ] **POISS-01**: Validate Poisson calibration against historical frequencies — run `calibrate_poisson_params()` and tune `POISSON_DRAW_ADJUSTMENT`
- [ ] **API-01**: Implement `enrich_with_api_stats` team name fuzzy matching for API-Football xG/possession data

## Out of Scope

- Real-time betting integration
- Multi-league expansion (Argentina only)
- Deep learning models
- Coordinator-Worker agent architecture
