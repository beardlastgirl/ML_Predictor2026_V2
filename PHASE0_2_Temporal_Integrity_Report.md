# Phase 0.2 — Same-Timestamp Leakage Elimination and Temporal Integrity Proof

**Status:** COMPLETE
**Date:** 2026-10-09
**Priority:** HIGH
**Depends on:** Phase 0.1 (Date+Time sorting fix)

---

## Executive Summary

Phase 0.1 corrected the pipeline to sort by Date+Time, but matches sharing an identical kickoff timestamp were still processed **sequentially**: each match updated Elo ratings and trailing history before the next match at the same timestamp computed its features. In Liga Profesional, most matches on a date are simultaneous or overlapping, so no result may influence another same-timestamp match's pre-match features.

Phase 0.2 replaces sequential processing with **atomic timestamp batches**: every match at a timestamp computes features from the same pre-batch state, and state updates are applied only after the whole batch is recorded. Dates containing unreliable kickoff times (missing, malformed, or 00:XX) are conservatively treated as a single day-long batch.

The post-fix baseline is unchanged within noise (mean accuracy 0.4324 vs 0.4326, mean log loss 1.1028 vs 1.1025), confirming the Phase 0.1 finding that this leakage had minimal aggregate impact. **The value of this fix is correctness, not performance.**

---

## 1. Verified Fixes

### 1.1 Atomic timestamp batching (new module)

**File:** `src/batched_features.py` (new)

Three public functions:

| Function | Purpose |
|----------|---------|
| `prepare_temporal_batches(matches_df)` | Normalizes Date+Time, assigns each row a `_temporal_batch` key, sorts chronologically (stable), assigns `_temporal_row_id` for feature alignment |
| `calculate_all_elo_ratings_batched(matches_df, base_elo)` | Per batch: record pre-match Elo for every match first, accumulate per-team Elo deltas, apply all deltas only after the batch completes |
| `compute_trailing_features_batched(matches_df, window)` | Per batch: compute trailing features for every match from pre-batch history first, then append the batch's results to team history in a deterministic (identity-sorted) order |

**Batch algorithm (prevents leakage):**

1. Parse `Date` (dayfirst-tolerant) and `Time` (stripped, `%H:%M`).
2. A time is **unreliable** if missing, unparseable, or `00:00`–`00:59` (the audit's 1,250 midnight records; real Liga Profesional matches do not kick off after midnight local time, so these are treated as unknown times).
3. If **any** match on a date has an unreliable time, the entire date becomes one batch keyed at midnight — an uncertain-time result can never be assumed available to another match that day. Otherwise the batch key is the full timestamp.
4. Iterate batches in chronological order. Within a batch, compute every match's Elo/trailing/Poisson-relevant inputs from the pre-batch state; only afterwards apply updates.
5. Within-batch history appends use a stable identity sort (`Home + Away`), so post-batch state is independent of input row order.

**Elo semantics check:** for the normal case (a team appears at most once in a batch), the batched update is numerically identical to the sequential `update_elo` semantics, including the [800, 2800] clip (`clip(pre + (clipped_new - pre)) == clipped_new`). For the degenerate case of a team appearing twice in one batch (not physically possible; only in stress-test data), deltas computed against the same pre-batch rating are summed — a deliberate conservative choice, since no ordering of simultaneous matches is defensible.

### 1.2 Integration into the production paths

| File | Change |
|------|--------|
| `src/pipeline.py` | `load_data` sorts via `prepare_temporal_batches` (Date+Time, conservative day batching). `build_features` calls `prepare_temporal_batches` once to establish the canonical order, then `calculate_all_elo_ratings_batched` and `compute_trailing_features_batched`; Elo history is joined back by `_temporal_row_id`. Poisson features are computed downstream of batched Elo/trailing features, so they inherit the corrected pre-match state. |
| `src/stats_engine.py` | `calculate_all_elo_ratings` is now a compatibility wrapper delegating to the batched implementation (single source of truth; no parallel implementation). |
| `src/features.py` | `compute_trailing_features` delegates to the batched implementation. `get_all_teams_latest_stats` (used by the prediction path) now uses a **stable** Date sort so the canonical batch order produced by the pipeline is preserved when building post-history stats for fixtures. |
| `src/model_engine.py` | Unchanged. Verified: `predict_gameweek` consumes only post-history aggregates (final Elo dict, final trailing stats) for future fixtures whose results do not exist yet — no same-timestamp leakage is possible on this path. |

**Paths inspected for leakage (all covered):**

| Path | Status |
|------|--------|
| Training features (`build_features`) | Batched |
| CV folds (`train_validate` via `TimeSeriesSplit`) | Features are pre-computed with per-match pre-match state; folds only split rows. A batch straddling a train/val boundary is safe because the validation match's features never include its batch-peers' results. Monotonic-index guard retained. |
| Public Elo/trailing APIs | Delegate to batched implementations |
| Prediction (`predict_gameweek`) | Post-history aggregates only; stable sort fix applied |

### 1.3 Preserved behavior

- Feature schema unchanged: same 24 `FEATURE_COLUMNS`.
- Row counts: 6,295 in -> 6,295 out of `build_features`; 6,261 eligible after `dropna(FEATURE_COLUMNS)` (identical to Phase 0.1).
- Target alignment: labels (`Res`) travel with their rows through the canonical sort; `X`/`y` share the same index in `train_validate`.
- All hyperparameters, model configuration, and evaluation methodology unchanged (`src/config.py` untouched).
- Prediction interface (`predict_gameweek`, `predict_fixtures`, `write_outputs`) unchanged.

---

## 2. Tests That Demonstrate the Fixes

**File:** `tests/test_temporal_ordering.py` (rewritten; 8 tests, all exercise the real production `build_features` path, not helpers in isolation)

| Requirement | Test | Result |
|-------------|------|--------|
| A. Unsorted input | `test_unsorted_input_is_sorted_before_production_features` | PASS |
| B. Same-timestamp isolation | `test_same_timestamp_result_change_cannot_change_peer_features` | PASS |
| C. Shared-team collision | `test_shared_team_collision_uses_one_pre_batch_snapshot` | PASS |
| D. Next-batch updates | `test_completed_batch_updates_the_next_batch` | PASS |
| E. Regression sensitivity | `test_regression_fixture_fails_under_old_sequential_semantics` | PASS |
| F. Ordering invariance | `test_row_order_inside_timestamp_batch_is_invariant_by_match_identity` | PASS |
| G. Future-result isolation | `test_future_result_cannot_change_earlier_timestamp_features` | PASS |
| Missing/unreliable times | `test_missing_or_midnight_time_batches_the_entire_uncertain_day` | PASS |

### Sensitivity evidence (requirement E)

The tests were executed against the **old sequential semantics** by monkeypatching `prepare_temporal_batches` in-memory to assign every row its own batch (production code never modified; scratch script deleted after use):

```
FAILED test_same_timestamp_result_change_cannot_change_peer_features
       (peer Home_Elo 1523.95 vs 1493.95 when batch-peer result flipped)
FAILED test_shared_team_collision_uses_one_pre_batch_snapshot
       (1512.23 vs 1523.95 — second same-timestamp match saw updated Elo)
FAILED test_regression_fixture_fails_under_old_sequential_semantics
FAILED test_missing_or_midnight_time_batches_the_entire_uncertain_day
4 failed, 4 passed — exit code 1
```

The 4 tests that still passed under sequential semantics are exactly the ones that must hold in both worlds (sorting, next-batch propagation, future isolation, disjoint-team invariance), confirming they are not brittle. Under the production batched code, all 8 pass.

### Full test suite

```
pytest tests/ -v
94 passed in 228.70s (0 failures, 0 errors)
```

Includes the golden-math suite (exact numerical snapshots for Elo/Poisson/Shin unchanged), the pre-existing leakage test, and the pipeline integration suite (feature presence, Elo bounds, CV metric ranges, output files).

---

## 3. Measured Evaluation Results

Reproduced with the exact production path (`load_data` -> `build_features` -> `train_validate`). Model configuration and evaluation methodology unchanged from Phase 0.1.

| Item | Value |
|------|-------|
| Dataset | `data/ARG.csv`, 6,295 rows, 2012-08-03 .. 2026-08-12 |
| Eligible samples | 6,261 (34 dropped for NaN features, same as Phase 0.1) |
| Features | 24 (unchanged schema) |
| Batches | 3,580 unique timestamps; 1,265 multi-match batches covering 3,980 matches |
| Unreliable times | 1,250 matches at 00:XX -> 3,297 matches on 1,060 dates conservatively day-batched |
| Model | CatBoost, `MODEL_PARAMS["catboost"]`, random_state=42 |
| CV | `TimeSeriesSplit(n_splits=5)` on the monotonically ordered index; sample weight 0.7 for draws |
| Class encoding | 0=Away (1,672), 1=Draw (1,889), 2=Home (2,700) |

### Per-fold results

| Fold | Train n | Train range | Val n | Val range | Accuracy | Log loss |
|------|---------|-------------|-------|-----------|----------|----------|
| 1 | 1,046 | 2012-08-10..2015-04-05 | 1,043 | 2015-04-05..2017-06-28 | 0.4286 | 1.1022 |
| 2 | 2,089 | ..2017-06-28 | 1,043 | ..2020-12-06 | 0.4353 | 1.1009 |
| 3 | 3,132 | ..2020-12-06 | 1,043 | ..2022-09-19 | 0.4353 | 1.1086 |
| 4 | 4,175 | ..2022-09-19 | 1,043 | ..2024-08-24 | 0.4487 | 1.0942 |
| 5 | 5,218 | ..2024-08-24 | 1,043 | ..2026-08-12 | 0.4142 | 1.1080 |

### Aggregate comparison with Phase 0.1 (post-sort, pre-batch)

| Metric | Phase 0.1 | Phase 0.2 | Delta |
|--------|-----------|-----------|-------|
| Mean accuracy | 0.4326 (+/- 0.0133) | **0.4324 (+/- 0.0112)** | -0.0002 |
| Mean log loss | 1.1025 (+/- 0.0054) | **1.1028 (+/- 0.0053)** | +0.0003 |
| Multiclass Brier (OOF, see convention) | ~0.666 (audit) | **0.6662** | ~0 |

**Brier convention:** computed on 5,215 out-of-fold predictions (fold 1's training segment has no OOF predictions) as `mean over rows of sum over the 3 classes of (p - y_onehot)^2`. This is the standard multiclass Brier score with range [0, 2]; it is not directly comparable to a binary Brier score.

**Interpretation:** Folds 1–3 are identical to 4 decimal places; folds 4–5 differ slightly because batching changes features only for matches sharing a timestamp and for the conservatively day-batched dates. The aggregate difference is far inside run-to-run noise. **No accuracy improvement is claimed** — the leakage had minimal aggregate impact on this dataset, but the corrected semantics are the only defensible ones.

---

## 4. Known Limitations

1. **Midnight kickoff times (00:XX):** 1,250 matches carry 00:00–00:59 times that are almost certainly data-entry placeholders rather than true kickoff times. They are not trusted: any date containing one is processed as a single day-long batch (3,297 matches on 1,060 dates). This is conservative — matches with known times on such a date forfeit the (unknowable) intra-day ordering information rather than risking contamination. The underlying data quality issue is upstream (football-data.co.uk) and out of scope.
2. **Conservatism cost:** on day-batched dates, later matches legitimately played later that day cannot use earlier same-day results. This slightly reduces feature freshness on ~17% of dates and is the intended trade-off.
3. **Trailing-window composition at batch boundaries:** for final prediction stats, which same-timestamp matches fall inside the trailing-8 window is determined by a deterministic but arbitrary identity ordering. This is an inherent ambiguity of simultaneous matches, not leakage.
4. **CV splitter:** `train_validate` currently uses plain `TimeSeriesSplit` (tournament-aware splitter exists in `src/cv_split.py` but is not wired in). Left unchanged — evaluation methodology was frozen for this phase.
5. **Brier score** is reported with its exact convention above; the Phase 0 audit's `~0.666` was never independently documented, so cross-phase comparison is approximate.

## 5. Remaining Risks

- If a future data source supplies trustworthy intra-day ordering for the 00:XX dates, `prepare_temporal_batches` can be relaxed per-date; until then the conservative default should remain.
- `prepare_temporal_batches` raises `ValueError` on unparseable dates rather than guessing; any new data source with dirty dates will fail loudly (intended, but worth knowing at ingestion time).
- Same-timestamp batching assumes the timestamp is the finest trustworthy ordering. Matches ordered within a timestamp by external knowledge (e.g., staggered kickoffs not present in the data) cannot be exploited.

---

## 6. Verdict

**Verified.**

- Same-timestamp leakage eliminated in the production feature-generation path (Elo, trailing stats, Poisson-derived features), proven by production-path tests that demonstrably fail under the old sequential semantics.
- Conservative handling of unreliable kickoff times implemented and tested.
- Full suite: 94/94 passing.
- Baseline reproduced with measured, fold-level evidence: mean accuracy 0.4324, mean log loss 1.1028 — statistically indistinguishable from the Phase 0.1 post-sort baseline, as expected for a correctness fix.

**Files changed:** `src/batched_features.py` (new), `src/pipeline.py`, `src/stats_engine.py`, `src/features.py`, `tests/test_temporal_ordering.py` (rewritten), plus this report. Scratch verification scripts were deleted after use.

**Phase 1 (Team State / news features) may proceed.**
