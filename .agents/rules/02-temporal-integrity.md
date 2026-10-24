# Temporal Integrity & Leakage Prevention Rules

## Phase 0 Architectural Contract

1. **Mandatory Batched Processing**:
   - All feature generation and Elo rating calculations MUST route through `src/batched_features.py`.
   - Never implement parallel, unbatched loops over historical matches.

2. **Temporal Sorting Invariant**:
   - Matches must always be sorted chronologically by `["Date", "Time"]` before computing any trailing statistics or ratings.
   - For matches sharing identical dates and missing/malformed kickoff times, conservative day-batches must be used.

3. **Pre-Batch State Sharing**:
   - Matches occurring within the same timestamp batch MUST share the identical pre-batch state (ratings, trailing form, xG metrics).
   - Rating updates and trailing statistics are applied only AFTER the entire batch finishes processing.

4. **Zero Future Lookahead**:
   - Feature functions must never incorporate statistics, goals, cards, or results from the current match or any future matches.
   - Any proposed feature must pass `tests/test_temporal_ordering.py` and `tests/test_leakage.py` without exceptions.
