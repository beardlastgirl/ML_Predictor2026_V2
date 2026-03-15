# Testing Patterns

**Analysis Date:** 2026-03-15

## Test Framework

**Runner:**
- pytest 7.4+
- Config: No `pytest.ini` or `conftest.py` (default discovery)

**Assertion Library:**
- Built-in `assert` with `pytest.approx` for floating point

**Run Commands:**
```bash
python -m pytest tests/test_main.py           # Run all tests
python -m pytest tests/test_main.py -v        # Verbose output
python -m pytest tests/test_main.py::test_name  # Single test
```

## Test File Organization

**Location:**
- Separate directory: `tests/`
- Co-located naming: `test_main.py` (tests main.py and all src modules)

**Naming:**
- `test_*.py` pattern for discovery
- Test functions: `test_<function_name>_<case>()`

**Structure:**
```
tests/
└── test_main.py          # All tests in single file (359 lines)
```

## Test Structure

**Suite Organization:**
```python
# Test class organization by feature area
# ==============================================
# Test Team Name Normalization
# ==============================================

def test_normalize_team_name_basic():
    """Test basic team name normalization."""
    assert normalize_team_name("boca juniors") == "BOCA JUNIORS"

# ==============================================
# Test Elo Calculations
# ==============================================

def test_expected_result():
    """Test expected result calculation."""
    assert expected_result(1500, 1500) == pytest.approx(0.5, abs=0.01)
```

**Patterns:**
- Section headers with comment dividers
- Descriptive docstrings explaining test purpose
- Arrange-Act-Assert implicit pattern
- No setup/teardown (stateless tests)

## Mocking

**Framework:** None currently used

**Patterns:**
- No mocking in current test suite
- All tests use real function calls
- Tests are unit-style but call actual implementations

**What to Mock:**
- Not applicable (no mocking patterns established)

**What NOT to Mock:**
- Pure functions (math in `stats_engine`)
- Data transformations (normalization functions)

## Fixtures and Factories

**Test Data:**
```python
# Inline test data construction
history = [
    {'gf': 2, 'ga': 1},  # Win
    {'gf': 1, 'ga': 0},  # Win
    {'gf': 0, 'ga': 0},  # Draw
]
stats = get_team_trailing_stats(history, 8)
```

**Location:**
- No fixtures directory
- Test data inline in test functions
- pandas DataFrames constructed inline for integration tests

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
# No coverage configured
# Would require: pytest --cov=src tests/
```

## Test Types

**Unit Tests:**
- Scope: Individual functions (25 test functions in `tests/test_main.py`)
- Approach: Direct function calls with known inputs/outputs
- Coverage:
  - Team name normalization (3 tests)
  - Elo calculations (5 tests)
  - Poisson distribution (12 tests)
  - Trailing features (5 tests)
  - Integration (2 tests)

**Integration Tests:**
- Scope: Complete workflows
- Approach: `test_poisson_workflow`, `test_elo_with_poisson`
- Tests multiple functions together

**E2E Tests:**
- Not used
- No end-to-end pipeline tests

## Common Patterns

**Floating Point Assertions:**
```python
assert total_prob == pytest.approx(1.0, abs=0.001)
assert outcomes['draw'] == pytest.approx(0.25, abs=0.05)
```

**Bounds Testing:**
```python
for _ in range(10):
    xG_home, xG_away = calculate_expected_goals(...)
    assert 0.2 <= xG_home <= 4.0
    assert 0.2 <= xG_away <= 4.0
```

**Property Testing:**
```python
# Probabilities must sum to 1
total = outcomes['home_win'] + outcomes['draw'] + outcomes['away_win']
assert total == pytest.approx(1.0, abs=0.001)
```

**Error Testing:**
- Not currently used
- No `pytest.raises` patterns

## Test Coverage Gaps

**Not Tested:**
- `src/pipeline.py` - Main orchestration logic
- `src/model_engine.predict_gameweek` - Prediction logic
- `src/data_processing` - File loading functions
- All scraper scripts (`scrape_*.py`)
- `parse_reporte_pdfs.py` - PDF parsing
- `src/utils` - Logging utilities

**Priority:**
- High: `pipeline.py` (core orchestration)
- Medium: `predict_gameweek` (prediction logic)
- Low: Scrapers (external dependencies)

## Running Tests

**Current Command:**
```powershell
python -m pytest tests/test_main.py
```

**Test Output:**
```
tests/test_main.py::test_normalize_team_name_basic PASSED
tests/test_main.py::test_expected_result PASSED
...
25 passed in X.XXs
```

---

*Testing analysis: 2026-03-15*
