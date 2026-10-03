---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Operational — pipeline producing varied, realistic predictions
last_updated: "2026-07-18T02:54:30.187Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Current State

**Last Updated:** 2026-05-02

## Current Position

**Season:** Apertura 2026 — Fecha 9 complete (last regular round)
**Next:** Playoffs (format and dates TBD)
**Status:** Operational — pipeline producing varied, realistic predictions

## System Health

- 34/34 tests passing
- Scoreline bug fixed (was all-1-1)
- GF/GA column mapping fixed
- Season-start new-team detection active
- Poisson calibration utility available but not yet run against full history

## Key Parameters (src/config.py)

- BASE_GOAL_RATE = 2.22 (NaN fallback for new teams)
- HOME_BOOST = 1.15
- POISSON_DRAW_ADJUSTMENT = 0.85
- ML_POISSON_BLEND_RATIO = 0.6
- TRAILING_WINDOW = 8
- Elo bounds: 800–2800

## Pending

- Run `calibrate_poisson_params()` to validate POISSON_DRAW_ADJUSTMENT
- Implement `enrich_with_api_stats` team name mapping
- Decide on playoff blend ratio adjustment
