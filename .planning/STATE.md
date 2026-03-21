# Current State

## Current Position

**Milestone:** v2.0 — Initialization & Alignment  
**Phase:** Not started (defining requirements)  
**Plan:** —  
**Status:** Defining requirements and roadmap structure  
**Last activity:** 2026-03-21 — Milestone v2.0 requirements phase started

## Accumulated Context

### From v1.0 (Production Quality & Fixes)

**Key Learnings:**
- All 10 priority fixes implemented and deployed successfully
- Edge case handling is critical: division by zero, NaN/Inf, DataFrame alignment
- Three-stage draw calibration is effective (Poisson adjustment + home boost + ML blending)
- Elo bounds (800-2800) work well for Liga Profesional Argentina
- Time-series CV with sample weights prevents look-ahead bias

**System Strengths:**
- Modular architecture with clear separation of concerns
- Robust Poisson distribution implementation for goal modeling
- Flexible data pipeline supporting multiple scrapers (FBref, FootyStats, Sofascore, TyC, PDFs)
- Comprehensive test coverage (26 tests, all passing)

**Known Gaps (v2.0 Focus):**
- Betting odds not yet integrated (DATA-01)
- Time-series leakage prevention incomplete (DATA-02)
- Poisson calibration not formally validated (POISS-01)
- No baseline comparison implementation (MODEL-01)
- Agent architecture still monolithic (AGENT-01)

### Architecture Overview

```
[Scrapers] → [Local files: CSV/JSON/TXT]
             ↓
       [src/pipeline.py]
             ↓
    [Features] → [Train/Validate] → [Predict] → [Output]
             ↓
    [Resultados_*.txt + PNG]
```

**Key Modules:**
- `src/stats_engine.py` — Elo + Poisson math
- `src/features.py` — Trailing average computation
- `src/model_engine.py` — ML model + prediction
- `src/data_processing.py` — Data normalization

### Configuration Snapshot

**Key Parameters:**
- BASE_GOAL_RATE = 1.89 (Argentine league average)
- HOME_BOOST = 1.22 (home team scoring boost)
- POISSON_DRAW_ADJUSTMENT = 0.85x (draw calibration)
- ML_POISSON_BLEND_RATIO = 0.6 (60% ML, 40% Poisson)
- Elo bounds: 800–2800
- Trailing window: 8 matches
- Result encoding: H=2 (Home), D=1 (Draw), A=0 (Away)

## Blockers

None currently. System is production-ready and fully tested.
