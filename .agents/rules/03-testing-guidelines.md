# Testing Strategy & Test Tiers

## Test Execution Tiers

The test suite contains 149+ tests. To balance verification rigor with agent velocity, test execution is divided into three tiers:

### Tier 1: Fast Integrity & Math Guard (< 5 seconds)
Execute during active development or when modifying `src/stats_engine.py`, `src/features.py`, or `src/config.py`:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_golden_math.py tests/test_temporal_ordering.py tests/test_leakage.py -q
```
- Validates Poisson / Dixon-Coles mathematical invariants.
- Proves zero temporal leakage across concurrent timestamp batches.

### Tier 2: Pipeline Integration (< 30 seconds)
Execute when modifying pipeline stages, data processing, or model interfaces:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_integration.py tests/test_form_variants.py -q
```
- Validates load -> features -> train -> predict pipeline with synthetic/sub-sampled fixtures.

### Tier 3: Full Milestone Regression (~7 minutes)
Execute before committing major milestone deliverables or PRs:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
- All 149+ tests must pass with zero failures.
