# Handoff Document - ML_Predictor2026_V2

**Date**: 2026-10-09
**Status**: Phase 1.1 Complete — Sporting Form INCONCLUSIVE, Baseline Kept ✅ | Phase 1.2 (Model E) Next

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

### Phase 1.0 — Experiment Harness COMPLETE (commit `44e1b58`)
- `src/experiment_harness.py`: `python -m src.experiment_harness --name <exp>` -> appends full record to `experiments/results.jsonl` (id, timestamp, git commit, config, env versions, data sha256, fold boundaries/counts, per-fold + aggregate acc/LL/Brier, OOF confusion matrix, errors).
- Fold loop mirrors `train_validate` exactly (TimeSeriesSplit(5), draw weight 0.7, CatBoost seed 42).
- **Verification PASSED:** 2 baseline runs identical (exact float equality, tolerance achieved = 0); independently reproduced Phase 0.2 frozen baseline: acc 0.43241 / LL 1.10278 / Brier 0.66619, OOF n=5215, train counts [1046, 2089, 3132, 4175, 5218], val 1043 x5.
- Baseline confusion matrix (OOF, rows=true A/D/H, cols=pred A/D/H): [[334,92,981],[304,78,1177],[308,98,1843]] — model rarely predicts Draw/Away; documented as reference.

### Phase 1.1 — Sporting Form COMPLETE (commit `6aa996e`) — NEGATIVE RESULT
- D1 EWMA (hl 2/4/8) and D2 venue splits tested as separate variants via `--variant` on the harness.
- All 4 variants: mean LL slightly below baseline (best D1 hl2: 1.0992 vs 1.1028) but paired bootstrap 95% CIs all cross 0 -> INCONCLUSIVE.
- **Decision: baseline 24 features kept.** D3 not run (conditional rule not met). Details: `PHASE1_1_Sporting_Form_Results.md`.
- Variant machinery remains available (`--variant ewma_hl2|ewma_hl4|ewma_hl8|venue_split`); production path unchanged.
- Comparison tool: `python -m src.experiment_compare <baseline_name> <variant_name>` (paired match-level bootstrap CI).

### Remaining experiment order (Master Prompt §12, isolated + comparable):
1. ~~1.1 Model D~~ DONE — inconclusive
2. **1.2** Model E — Coaching change dates (curated CSV, verified dates; Transfermarkt/Wikipedia). NEXT.
3. **1.3** Model C — Squad availability: DATA AUDIT FIRST. If no free historical source with as-known-at-T timestamps exists, reject without building.
4. **1.4** Model G — News: deferred until harness proven; no sentiment-only scoring (Master Prompt §7).
5. **1.5** Model H — combine only components with proven OOF delta.

**Frozen architecture rule:** atomic timestamp batching is not revisited; any new time-dependent feature must consume pre-batch state only.

## Files to Read First Next Session
1. This file
2. `PHASE0_2_Temporal_Integrity_Report.md` (verdict: Verified)
3. `AGENTS.md` (project conventions)

## Worktree Hygiene
Many unrelated untracked files exist (scraper CSV outputs `src/fbref_*`, `src/footystats_*`, `outputs/`, `jobs/`). Do NOT stage them into feature commits. Uncommitted-but-unrelated: `Partidos.txt.bak`, `requirements.*`, `src/sofascore_stats.json`.
