# Roadmap

**Last Updated:** 2026-05-02

## Completed Phases

- [x] Phase 1: Data Foundation — odds integration, leakage prevention, header mapping
- [x] Phase 2: Model Baselines — naive + bookie log-loss comparison in output
- [x] Phase 3a: Scoreline fix — floor(xG), ML threshold, GF/GA fallback
- [x] Phase 3b: Season tooling — new-team detection, calibration utility, scraper fix

## Pending

- [ ] Phase 3c: Poisson Calibration — run `calibrate_poisson_params()`, tune `POISSON_DRAW_ADJUSTMENT`
- [ ] Phase 4: Playoff Support — optional blend ratio adjustment for knockout rounds
- [ ] Phase 5: API Enrichment — implement `enrich_with_api_stats` team name mapping

## Deferred (out of scope for now)

- Coordinator-Worker agent architecture (AGENT-01)
- Multi-league expansion
- Deep learning models
- Web dashboard
