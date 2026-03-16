# Roadmap - ML_Predictor2026_V2

## Milestone v2.0: Core Engine Rebuild & Calibration

Goal: Transform the system into a skillful prediction engine that beats naive baselines and provides realistic scoreline distributions.

## Phases

- [ ] **Phase 1: Data Alignment & Baselines** - Fix foundation with odds, features, and leakage-free validation.
- [ ] **Phase 2: Advanced Modeling** - Implement Dixon-Coles, scoring metrics, and goal calibration.
- [ ] **Phase 3: Agent Architecture** - Transition to autonomous Coordinator-Worker architecture.

## Phase Details

### Phase 1: Data Alignment & Baselines
**Goal**: Establish a robust, leakage-free data foundation and baseline performance metrics.
**Depends on**: Nothing
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, MODEL-01, MODEL-03
**Success Criteria**:
  1. Every training record has correctly aligned historical features and closing odds with zero look-ahead leakage.
  2. System produces baseline performance scores (naive, historical, bookmaker) for all historical test periods.
  3. Feature set is enriched with xG and form metrics without introducing data quality errors.
**Plans**: 3 plans
- [ ] 01-01-PLAN.md — Core Stats Engine & Data Processing (Odds & Implied Probs)
- [ ] 01-02-PLAN.md — Baselines & Validation Loop
- [ ] 01-03-PLAN.md — xG Enrichment & Data Merging

### Phase 2: Advanced Modeling
**Goal**: Implement advanced Poisson modeling and rigorous evaluation metrics.
**Depends on**: Phase 1
**Requirements**: MODEL-02, MODEL-04, MODEL-05
**Success Criteria**:
  1. Model produces scoreline distributions that match historical frequency better than mean-based Poisson.
  2. Predictions are evaluated using Log Loss and RPS, showing measurable improvement over baselines.
  3. Match outcome probabilities (1X2) are mathematically derived and consistent with predicted score distributions.
**Plans**: TBD

### Phase 3: Agent Architecture
**Goal**: Decouple system components into an autonomous Coordinator-Worker architecture.
**Depends on**: Phase 2
**Requirements**: AGENT-01, AGENT-02, AGENT-03
**Success Criteria**:
  1. System operates as a set of decoupled workers (Scraper, Trainer, Inference) managed by a central coordinator.
  2. Coordinator agent successfully orchestrates an autonomous "query-train-predict" cycle.
  3. System resilience is demonstrated by successful task completion despite individual worker restarts.
**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1: Data Alignment & Baselines | 0/3 | Not started | - |
| 2: Advanced Modeling | 0/0 | Not started | - |
| 3: Agent Architecture | 0/0 | Not started | - |
