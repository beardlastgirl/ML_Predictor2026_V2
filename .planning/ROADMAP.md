# Roadmap — Milestone v2.0: Initialization & Alignment

**Created:** 2026-04-10  
**Granularity:** Coarse  
**Coverage:** 5/5 requirements mapped

---

## Phases

- [ ] **Phase 1: Data Foundation** — Integrate odds and prevent data leakage
- [ ] **Phase 2: Model Baselines** — Implement naive and bookie comparison models
- [ ] **Phase 3: Poisson Calibration** — Calibrate scoreline distributions
- [ ] **Phase 4: Agent Architecture** — Evolve to Coordinator-Worker pattern

---

## Phase Details

### Phase 1: Data Foundation
**Goal**: Clean, leakage-free data pipeline with betting odds integration  
**Depends on:** Nothing (first phase)  
**Requirements:** DATA-01, DATA-02  
**Success Criteria** (what must be TRUE):
  1. User can run pipeline with betting odds included as model features
  2. User can verify no future data leaks in time-series splits (validation passes)
  3. User can access closing odds for calibration baseline comparison
**Plans:** TBD

### Phase 2: Model Baselines
**Goal**: Establish performance baselines for model comparison  
**Depends on:** Phase 1 (needs odds data for bookie baseline)  
**Requirements:** MODEL-01  
**Success Criteria** (what must be TRUE):
  1. User can run naive baseline (historical average) and see accuracy score
  2. User can run bookie baseline (odds-derived probabilities) and see log-loss score
  3. User can compare ML model performance against both baselines in output report
**Plans:** TBD

### Phase 3: Poisson Calibration
**Goal**: Realistic scoreline probability distributions from Poisson model  
**Depends on:** Phase 1 (needs clean data)  
**Requirements:** POISS-01  
**Success Criteria** (what must be TRUE):
  1. User sees scoreline probabilities that sum to 1.0 across all outcomes
  2. User observes realistic goal distributions (0-5 goals typical, rare 6+ goals)
  3. User can compare predicted vs actual scoreline frequencies (calibration plot)
**Plans:** TBD

### Phase 4: Agent Architecture
**Goal**: Modular Coordinator-Worker agent structure for extensibility  
**Depends on:** Phase 1 (needs stable data pipeline)  
**Requirements:** AGENT-01  
**Success Criteria** (what must be TRUE):
  1. User can invoke Coordinator agent to orchestrate prediction workflow
  2. User can see Worker agents execute specialized tasks (data, model, stats)
  3. User can add new Worker agent without modifying Coordinator logic
**Plans:** TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/0 | Not started | - |
| 2. Model Baselines | 0/0 | Not started | - |
| 3. Poisson Calibration | 0/0 | Not started | - |
| 4. Agent Architecture | 0/0 | Not started | - |

---

## Requirement Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| MODEL-01 | Phase 2 | Pending |
| POISS-01 | Phase 3 | Pending |
| AGENT-01 | Phase 4 | Pending |
