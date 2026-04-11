# Requirements — Milestone v2.0: Initialization & Alignment

**Status:** Active  
**Last Updated:** 2026-04-10

---

## Active Requirements

### DATA — Data Pipeline

- [ ] **DATA-01**: Integrate betting odds as features and calibration baselines
  - Scrape historical odds from bookmakers
  - Add odds as ML model features
  - Use closing odds for model calibration baseline

- [ ] **DATA-02**: Improve data alignment and leakage prevention (time-series)
  - Validate chronological integrity of all features
  - Prevent look-ahead bias in trailing averages
  - Add time-series split validation tests

### POISS — Poisson Model

- [ ] **POISS-01**: Calibrate Poisson model for realistic scoreline distributions
  - Validate goal distributions match historical frequencies
  - Calibrate BASE_GOAL_RATE per season/team
  - Verify scoreline probabilities sum to 1.0

### MODEL — Model Performance

- [ ] **MODEL-01**: Implement baseline performance comparisons (naive, bookie)
  - Naive baseline: historical outcome frequencies
  - Bookie baseline: odds-derived probabilities
  - Report comparison metrics in output

### AGENT — Agent Architecture

- [ ] **AGENT-01**: Evolve to Coordinator-Worker agent architecture
  - Define Coordinator agent for orchestration
  - Create Worker agents for specialized tasks (data, model, stats)
  - Enable extensibility for new Workers

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| MODEL-01 | Phase 2 | Pending |
| POISS-01 | Phase 3 | Pending |
| AGENT-01 | Phase 4 | Pending |

---

## Out of Scope

- Real-time betting integration (focus on batch prediction)
- Multi-league expansion (focused on Argentina)
- Deep learning models (maintaining tree-based + Poisson)
