# Handoff Document - ML_Predictor2026_V2

**Date**: 2026-10-10
**Status**: Phase 1.2 Complete — Rolling Performance INCONCLUSIVE, Baseline Kept ✅ | Model E REJECTED (feasibility) | Model C Data Audit COMPLETE — Partial Feasibility

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
149/149 PASSING (~435s)
- tests/test_temporal_ordering.py:  8 tests (production-path; fail under old sequential semantics — sensitivity proven)
- tests/test_golden_math.py:       17 tests
- tests/test_main.py:              29+ tests
- tests/test_pipeline_integration: 19 tests
- tests/test_scraper_utils.py:     15 tests
- tests/test_leakage.py:            1 test
- tests/test_form_variants.py:     14 tests (Phase 1.1 + 1.2 variant tests)
```

---

## Key Architecture Facts
- `src/batched_features.py` — canonical temporal batching (do not create parallel implementations)
- `src/config.py` — all hyperparameters; never hardcode elsewhere
- Elo/trailing/Poisson features derive from one canonical order: `prepare_temporal_batches`
- Class encoding: 0=Away, 1=Draw, 2=Home
- `src/cv_split.py` tournament-aware CV is now wired into `train_validate` (date-gap boundaries); early stopping enabled

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

### Phase 1.2 — Rolling Team Performance COMPLETE (this session) — NEGATIVE RESULT
- Candidate set: rolling PPG and GD per match over previous 5 and 10 matches (8 features, a priori windows [5,10] from `config.ROLLING_WINDOW_CANDIDATES`).
- Overlap audit (Deliverable 1): all 4 candidates in "marginal" correlation band (0.85–0.95) vs. existing features and already-tested EWMA variants; none fully redundant (≥0.95).
- Experiment: `roll_windows` variant via `--variant roll_windows` on harness. Mean LL 1.1021 vs baseline 1.1064 (delta −0.00425), Brier 0.6654 vs 0.6684 (delta −0.00295).
- Paired bootstrap 95% CI: LL [−0.00865, +0.00019] crosses 0 → **INCONCLUSIVE** (same pattern as Phase 1.1).
- **Decision: baseline 24 features kept.** Details: `PHASE1_2_Rolling_Performance_Results.md`.

### Model E (Coaching Changes) — REJECTED
- Feasibility audit `MANAGER_DATA_FEASIBILITY_AUDIT.md` shows historical manager data coverage 0.3% on full history (~56% modern era only), point-in-time reliability insufficient for pre-2010 seasons.
- **Recommendation: do not build coaching features** — cannot populate genuine historical, point-in-time values for the backtesting required by the harness.

### Model C (Squad Availability) — DATA AUDIT COMPLETE
- Feasibility audit `SQUAD_AVAILABILITY_FEASIBILITY_AUDIT.md` completed.
- **Injuries**: NOT FEASIBLE — no free historical source with point-in-time publication dates at scale. Transfermarkt injury dates are retrospective; news extraction impractical at 14yr×45 clubs.
- **Suspensions**: CONDITIONALLY FEASIBLE — requires player-level match events (cards per player per match). ARG.csv lacks this. No free source confirmed for 2012-2026 Argentina.
- **National Team Call-ups**: FEASIBLE — AFA PDF convocation lists 2012+ with publication dates (~10 days pre-FIFA window). ~5-10% of matches affected.
- **Recommendation**: Do NOT build combined "squad availability" feature. Injuries (majority of unavailability) missing. Test call-ups only IF player-event source found for suspensions, else reject Model C.

### Remaining experiment order (Master Prompt §12, isolated + comparable):
1. ~~1.1 Model D (sporting form)~~ DONE — inconclusive
2. ~~1.2 Rolling performance~~ DONE — inconclusive
3. ~~1.3 Model E (coaching)~~ **REJECTED** — `MANAGER_DATA_FEASIBILITY_AUDIT.md` (insufficient historical coverage/point-in-time reliability)
4. **1.4 Model C** — Squad availability: **AUDIT DONE — PARTIAL FEASIBILITY**
   - Injuries: REJECT (no point-in-time source)
   - Suspensions: BLOCKED (need player-event data source — not in ARG.csv)
   - Call-ups: FEASIBLE (AFA PDFs) but low coverage (~5-10% matches)
   - **Decision gate**: Find free player-event data (cards/minutes per player per match) for 2012-2026 Argentina. If none → REJECT Model C.
5. **1.5 Model G** — News: deferred until harness proven; no sentiment-only scoring (Master Prompt §7).
6. **1.6 Model H** — Combine only components with proven OOF delta (none to date).

**Frozen architecture rule:** atomic timestamp batching is not revisited; any new time-dependent feature must consume pre-batch state only.

## Files to Read First Next Session
1. This file
2. `PHASE1_4_1_Closure_Report.md` — closes all handoff metric discrepancies
3. `MODEL_C_REJECTION_REPORT.md` ← **NEW — Model C formally rejected; roadmap exhausted**
4. `AGENTS.md` (project conventions)

## Phase 1.4.1 — CLOSED (2026-10-10)
All metric discrepancies from the handoff are resolved. See `PHASE1_4_1_Closure_Report.md`.
- Brier 0.666 vs 0.5448: different data snapshots (6295 vs 6399 rows), same formula.
- 55.4% accuracy diagnostic: in-sample prediction on a globally-trained model — not OOF; invalid.
- TimeSeriesSplit vs tournament-aware CV: all evaluations use TimeSeriesSplit(5); cv_split.py not wired.
- Phase 1.4 NO-GO confirmed: Brier degrades +20.2%; candidate not promoted.

## Model C — REJECTED (2026-10-10)
Decision gate failed. ARG.csv has 25 columns, all match-level — no player events. Reporte PDFs extract results only. FBref/FootyStats/Sofascore/Transfermarkt all lack free historical player-event data for 2012–2026 Argentina. See `MODEL_C_REJECTION_REPORT.md`.

## Experiment Roadmap — EXHAUSTED
All proposed feature additions rejected or inconclusive:
- D (sporting form): INCONCLUSIVE
- D (rolling windows): INCONCLUSIVE  
- E (coaching): REJECTED — no data
- C (squad availability): REJECTED — no data
- 1.4 (market odds): NO-GO — Brier degrades

**Next recommended action:** Probability calibration experiment (Platt/isotonic on OOF, not on held-out fold) to investigate why Phase 1.4 improved LL/acc but degraded Brier. Requires explicit user confirmation before starting — not currently in plan.

## Worktree Hygiene
Many unrelated untracked files exist (scraper CSV outputs `src/fbref_*`, `src/footystats_*`, `outputs/`, `jobs/`). Do NOT stage them into feature commits. Uncommitted-but-unrelated: `Partidos.txt.bak`, `requirements.*`, `src/sofascore_stats.json`.
