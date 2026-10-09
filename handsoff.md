# Handoff Document - ML_Predictor2026_V2

**Date**: 2026-10-09
**Status**: Phase 0.2 Complete — Temporal Integrity Verified ✅ | Phase 1 Ready

---

## Session Skills Mandate (applies every session)

Load and apply at session start:
- `C:\Scripts\MainSkills\model-routing\SKILL.md`
- `C:\Scripts\MainSkills\token-optimization-context-defense\SKILL.md`
- `C:\Scripts\MainSkills\python-code-review\python-code-review-skill.md`

---

## Project Location
Local Project Root: `C:\Scripts\ML_Predictor2026_V2\`

**Execution:** Always run Python as modules from root: `python -m src.module_name` (avoids `src.paths` import errors).

---

## Current State (2026-10-09)

### Temporal Integrity — COMPLETE (commit `275d462`)
- **Phase 0.1**: Fixed Date-only sorting → sort by `["Date", "Time"]` in `src/pipeline.py`.
- **Phase 0.2**: Atomic timestamp batches via `src/batched_features.py` — same-timestamp matches share one pre-batch state; Elo/trailing updates apply only after the batch. Dates with missing/malformed/00:XX times (1,250 matches) become conservative day-batches (3,297 matches on 1,060 dates).
- Public APIs (`calculate_all_elo_ratings`, `compute_trailing_features`) delegate to the batched path — single implementation.
- Prediction path (`predict_gameweek`) verified safe; `get_all_teams_latest_stats` now uses stable sort.
- Reports: `PHASE0_1_Temporal_Integrity_Report.md`, `PHASE0_2_Temporal_Integrity_Report.md`.

### Baseline Metrics (post-fix, measured 2026-10-09)
| Metric | Value |
|--------|-------|
| Dataset | `data/ARG.csv`, 6,295 rows (2012-08-03..2026-08-12), 6,261 eligible |
| Features | 24 (schema unchanged) |
| Model | CatBoost, random_state=42, draw weight 0.7 |
| CV | TimeSeriesSplit(5) |
| Mean Accuracy | 0.4324 ± 0.0112 |
| Mean Log Loss | 1.1028 ± 0.0053 |
| Multiclass Brier (OOF, 3-class SSE) | 0.6662 |

### Tests
```
94/94 PASSING (~229s)
- tests/test_temporal_ordering.py:  8 tests (production-path; fail under old sequential semantics — sensitivity proven)
- tests/test_golden_math.py:       17 tests
- tests/test_main.py:              29+ tests
- tests/test_pipeline_integration: 19 tests
- tests/test_scraper_utils.py:     15 tests
- tests/test_leakage.py:            1 test
```

---

## Key Architecture Facts
- `src/batched_features.py` — canonical temporal batching (do not create parallel implementations)
- `src/config.py` — all hyperparameters; never hardcode elsewhere
- Elo/trailing/Poisson features derive from one canonical order: `prepare_temporal_batches`
- Class encoding: 0=Away, 1=Draw, 2=Home
- `src/cv_split.py` tournament-aware CV exists but is NOT wired into `train_validate` (plain TimeSeriesSplit in use)

## Operational Notes
- Weekly: update `Partidos.txt`, run `python main.py` (or `.\run_model.ps1`)
- FBref/FootyStats blocked (403); use CDP method `python -m src.scrape_stats_manual` with manual CAPTCHA
- New teams → add mappings to `Glossary.txt`

## Known Issues
1. 1,250 midnight (00:XX) kickoff times are data artifacts — conservatively day-batched, not trusted
2. Scraper fragility (DOM changes); triple-source strategy mitigates
3. Manual Glossary mapping for new teams
4. Model at naive-baseline-ish performance; no accuracy gain expected/claimed from temporal fix

## Phase 1 Plan (agreed 2026-10-09)

**Objective (RESOLVED):** Track both 3-class and goals metrics; a feature ships ONLY if 3-class log loss/Brier improves out-of-sample on identical folds. Goals metrics are informational.

Experiment order (Master Prompt §12, isolated + comparable):
1. **1.0** Experiment harness: one script runs a variant -> same TimeSeriesSplit(5) folds -> appends acc/LL/Brier + confusion matrix to results log. Freeze baseline: acc 0.4324 / LL 1.1028 / Brier 0.6662.
2. **1.1** Model D — Sporting Form variants (EWMA decay, home/away splits) from ARG.csv only. No new data needed.
3. **1.2** Model E — Coaching change dates (curated CSV, verified dates; Transfermarkt/Wikipedia).
4. **1.3** Model C — Squad availability: DATA AUDIT FIRST. If no free historical source with as-known-at-T timestamps exists, reject without building.
5. **1.4** Model G — News: deferred until harness proven; no sentiment-only scoring (Master Prompt §7).
6. **1.5** Model H — combine only components with proven OOF delta.

**Frozen architecture rule:** atomic timestamp batching is not revisited; any new time-dependent feature must consume pre-batch state only.

## Files to Read First Next Session
1. This file
2. `PHASE0_2_Temporal_Integrity_Report.md` (verdict: Verified)
3. `AGENTS.md` (project conventions)

## Worktree Hygiene
Many unrelated untracked files exist (scraper CSV outputs `src/fbref_*`, `src/footystats_*`, `outputs/`, `jobs/`). Do NOT stage them into feature commits. Uncommitted-but-unrelated: `Partidos.txt.bak`, `requirements.*`, `src/sofascore_stats.json`.
