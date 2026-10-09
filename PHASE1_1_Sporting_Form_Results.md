# Phase 1.1 — Sporting Form (Model D) Results

**Status:** COMPLETE — variants INCONCLUSIVE, baseline kept
**Date:** 2026-10-09
**Harness:** `src/experiment_harness.py` (Phase 1.0, verified deterministic)
**Baseline (frozen):** mean LL 1.10278, Brier 0.66619, acc 0.43241, OOF n=5,215

---

## Design

| Variant | Features added | Candidates |
|---------|---------------|------------|
| D1 — EWMA form | `Home/Away_EWMA_Form/GF/GA` (exponentially weighted, half-life h, window 8) | h in {2, 4, 8} — a priori set, no further tuning |
| D2 — Venue splits | `Home/Away_Venue_Form/GF/GA` (venue-matched trailing stats; fallback to overall when < 3 venue matches) | single configuration |

- All variant features computed inside the canonical batch architecture (`src/batched_features.py`, same pre-batch pass); NaN exactly where baseline trailing features are NaN → identical eligible rows (6,261), identical folds, identical OOF set (5,215). Harness raises if a variant changes the eligible set (checked: 0 rows affected).
- Poisson features intentionally kept on base trailing stats — variant signal enters only as added model features (clean attribution).
- Decision rule (predefined): ship only if mean OOF log-loss delta < 0 AND paired bootstrap 95% CI (10,000 resamples, match-level) excludes 0.

## Results (identical folds, CatBoost seed 42, draw weight 0.7)

| Variant | Mean LL | Mean Brier | Mean Acc | LL delta vs baseline [95% CI] | Verdict |
|---------|---------|------------|----------|-------------------------------|---------|
| D1 EWMA hl=2 | 1.0992 | 0.6643 | 0.4347 | **-0.00359 [-0.00875, +0.00164]** | INCONCLUSIVE |
| D1 EWMA hl=4 | 1.1002 | 0.6646 | 0.4339 | -0.00254 [-0.00670, +0.00165] | INCONCLUSIVE |
| D1 EWMA hl=8 | 1.1017 | 0.6656 | 0.4313 | -0.00110 [-0.00452, +0.00230] | INCONCLUSIVE |
| D2 venue split | 1.1020 | 0.6660 | 0.4274 | -0.00083 [-0.00569, +0.00398] | INCONCLUSIVE |

Per-fold LL deltas, D1 hl=2: f1 -0.0054, f2 -0.0070, f3 +0.0018, f4 -0.0009, f5 -0.0065 (4/5 folds negative).
D2: f1 +0.0022, f2 +0.0017, f3 +0.0064, f4 -0.0087, f5 -0.0058 (mixed sign).

## Interpretation

- D1 (EWMA) shows a **consistent direction** (all 3 half-lives improve mean LL; hl=2 negative in 4/5 folds), but the paired CIs all include 0. With 5 folds and ~5,215 OOF matches, an effect of this size (~0.3% LL) cannot be distinguished from noise. Accuracy gains (up to +0.23 pts for hl=2) are not the deciding metric and are within noise as well.
- D2 (venue splits) shows no consistent direction (3 folds worse, 2 folds better).
- **D3 (combined) not run**: it was conditional on credible evidence from D1 or D2; none met the rule.

## Decision

**Keep the baseline 24-feature configuration.** All variant code remains in the repository (inactive unless `--variant` is passed) so the experiment is reproducible; production `build_features()` behavior is unchanged.

This is a documented negative result, not a failure: the "recent form weighting" hypothesis at this effect size does not demonstrably improve 3-class probability quality on this dataset. Larger effect would be needed to be detectable with this OOF set.

## Evidence trail

- `experiments/results.jsonl` — 5 new records (baseline + D1 x3 + D2), full config/env/fold detail
- `experiments/oof_<experiment_id>.csv` — per-match OOF probabilities enabling the paired analysis
- `src/experiment_compare.py` — `python -m src.experiment_compare baseline D1_ewma_hl2` reproduces any verdict above
- Tests: `tests/test_form_variants.py` (8 tests: hand-computed EWMA values, NaN alignment, venue fallback, venue purity, same-timestamp batch isolation for both variants, baseline invariance). Full suite: **102/102 passed**.

## Note on the confusion-matrix observation

Baseline OOF confusion (rows=true A/D/H): [[334,92,981],[304,78,1177],[308,98,1843]] — Draw/Away under-predicted. This is a calibration/class-prior question, not evidence that form features are missing; D1/D2 results (no credible LL gain) support that reading. Any draw-recall work should target calibration or class weighting as its own isolated experiment.

## Next

Per plan: Phase 1.2 — Model E (Coaching change dates), which requires a curated, dated manager-history CSV before any modeling. Squad availability (Model C) remains gated on the data-availability audit.
