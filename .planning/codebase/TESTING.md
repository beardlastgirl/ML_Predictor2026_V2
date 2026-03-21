# Testing Patterns

**Analysis Date:** 2025-01-20

## Test Framework

**Runner:**
- pytest 7.4.0+ (from `requirements.txt`)
- Config: No pytest.ini, setup.cfg, or pyproject.toml configuration detected
- Default configuration (assumes pytest discovers tests in `tests/` directory)

**Assertion Library:**
- pytest's built-in assertions with `assert` statements
- `pytest.approx()` for floating-point comparison with tolerance
- Example from `tests/test_main.py` line 65:
  ```python
  assert expected_result(1500, 1500) == pytest.approx(0.5, abs=0.01)
  ```

**Run Commands:**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_main.py

# Verbose output
pytest -v

# Run specific test
pytest tests/test_main.py::test_normalize_team_name_basic

# Watch mode / continuous testing
pytest --watch  # if pytest-watch installed

# With coverage (if coverage installed)
pytest --cov=src tests/
```

## Test File Organization

**Location:**
- All tests in `tests/` directory at repository root
- Single test file: `tests/test_main.py`
- Colocated testing (not inline with source)

**Naming:**
- Test file: `test_main.py` (follows pytest convention: `test_*.py`)
- Test functions: `test_*` prefix (lines 40-356)
- Test classes: Not used in this codebase
- Descriptive test names: `test_normalize_team_name_basic`, `test_calculate_outcome_probabilities_sum`

**Structure:**
```
tests/
└── test_main.py          # All tests in single file
```

## Test File Content

**Organization by functionality (lines 36-356):**

1. **Data Processing Tests** (lines 36-56):
   - Team name normalization (basic, with glossary, special chars)

2. **Elo Calculation Tests** (lines 58-110):
   - Expected result calculation
   - Elo updates (home win, away win, draw)
   - Home advantage effect

3. **Poisson Distribution Tests** (lines 112-242):
   - Probability sum validation
   - Probability peak detection
   - Expected goals calculation (basic, strong attack, bounds)
   - Outcome probability calculation
   - Integration with Poisson features

4. **Trailing Features Tests** (lines 244-315):
   - Empty history handling
   - Single match handling
   - Form calculation
   - Window limiting
   - Full feature computation

5. **Integration Tests** (lines 317-356):
   - Complete Poisson workflow
   - Elo and Poisson integration

## Test Structure

**Setup Pattern:**
- Inline test data creation (no fixtures)
- Example from `tests/test_main.py` lines 257-265:
  ```python
  def test_get_team_trailing_stats_single_match():
      """Test trailing stats with single match."""
      history = [{'gf': 2, 'ga': 1, 'is_home': True}]
      stats = get_team_trailing_stats(history, 8)
      
      assert stats['avg_gf'] == 2
      assert stats['avg_ga'] == 1
      assert stats['avg_gd'] == 1
      assert stats['matches'] == 1
  ```

**Assertion Patterns:**
```python
# Direct equality
assert normalize_team_name("boca juniors") == "BOCA JUNIORS"

# Floating point approximation
assert expected_result(1500, 1500) == pytest.approx(0.5, abs=0.01)

# Range checks
assert 0.20 < outcomes['draw'] < 0.45

# Comparison
assert expected_result(1600, 1500) > 0.5

# Boolean checks
assert new_home > home_elo

# Membership
assert 'xG_home' in features
assert 0 <= features['Poisson_Home_Win'] <= 1
```

**Docstrings:**
- All test functions have docstrings describing what they test
- Example: `"""Test that home advantage is applied."""`

## Test Data / Fixtures

**Approach:**
- No pytest fixtures used (@pytest.fixture decorator not present)
- No conftest.py file
- Test data created inline within test functions

**Test Data Patterns:**

Simple scalar values:
```python
def test_expected_result():
    """Test expected result calculation."""
    assert expected_result(1500, 1500) == pytest.approx(0.5, abs=0.01)
```

Dictionary fixtures for team history:
```python
def test_get_team_trailing_stats_single_match():
    history = [{'gf': 2, 'ga': 1, 'is_home': True}]
    stats = get_team_trailing_stats(history, 8)
```

Match history list:
```python
def test_get_team_trailing_stats_form_win():
    history = [
        {'gf': 2, 'ga': 1},  # Win
        {'gf': 1, 'ga': 0},  # Win
        {'gf': 0, 'ga': 0},  # Draw
    ]
```

DataFrame fixtures:
```python
def test_compute_trailing_features_basic():
    matches = pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-08', '2024-01-15']),
        'Home': ['TeamA', 'TeamB', 'TeamA'],
        'Away': ['TeamB', 'TeamA', 'TeamB'],
        'Res': [2, 0, 2],
        'GF': [2, 1, 3],
        'GA': [1, 2, 0]
    })
```

## Mocking

**Framework:** Not used - no mock/patch imports in tests

**Patterns:**
- No external dependencies mocked
- All functions tested directly with real data
- No unittest.mock or pytest-mock usage

**What's Mocked:**
- Nothing (pure unit testing approach)

**What's NOT Mocked:**
- Pandas DataFrames (used directly)
- Numpy arrays (used directly)
- Scipy distributions (used directly)
- File I/O (not tested in current test suite)

## Coverage Analysis

**Tested Areas (lines visible in tests):**

| Component | Coverage | Location |
|-----------|----------|----------|
| Normalization | Full | Lines 40-56 |
| Elo math | Full | Lines 62-110 |
| Poisson distribution | Full | Lines 116-242 |
| Expected goals | Full | Lines 129-170 |
| Outcome probabilities | Full | Lines 172-205 |
| Trailing features | Full | Lines 247-315 |
| Integration workflows | Partial | Lines 321-356 |

**NOT Tested (Coverage Gaps):**

| Area | Why Important | File |
|------|---------------|------|
| Data loading | Critical | `src/data_processing.py` load_glossary(), load_sofascore_data(), parse_fixtures() |
| File I/O | Critical | Reading CSV, JSON, text files - no mocking means no test coverage |
| Model training | Important | `src/model_engine.py` create_model(), predict_gameweek() - no ML model tests |
| Pipeline orchestration | Important | `src/pipeline.py` run_pipeline(), train_validate(), build_features() |
| Error handling | Important | Exception paths in data loading (try/except blocks) |
| Data normalization edge cases | Medium | Accent handling, multiple delimiters in glossary parsing |
| Sofascore data parsing | Medium | Multiple JSON structure handling in load_sofascore_data() |
| Fixture parsing | Medium | parse_fixtures() with various score formats |
| Elo with new teams | Low | BASE_ELO initialization for unknown teams |
| Shin method odds extraction | Low | shin_method() odds calculation and edge cases |

## Test Types

**Unit Tests:**
- Scope: Individual functions in isolation
- Approach: Test each function with various inputs
- Examples:
  - `test_expected_result()` - Tests Elo expected result formula
  - `test_calculate_expected_goals_bounds()` - Tests xG clamping
  - `test_poisson_probability_sum()` - Tests probability distribution

**Integration Tests:**
- Scope: Multiple functions working together
- Approach: End-to-end workflow testing
- Examples (lines 321-356):
  - `test_poisson_workflow()` - Full Poisson calculation pipeline
  - `test_elo_with_poisson()` - Elo and Poisson integration

**E2E Tests:**
- Status: Not implemented
- Would require: File I/O, model training, full pipeline execution
- Framework: Would need fixtures for data files

## Common Test Patterns

**Boundary Testing:**
```python
def test_calculate_expected_goals_bounds():
    """Test that xG values stay within reasonable bounds."""
    for _ in range(10):
        xG_home, xG_away = calculate_expected_goals(
            elo_home=np.random.randint(1300, 1700),
            # ...
        )
        assert 0.2 <= xG_home <= 4.0
        assert 0.2 <= xG_away <= 4.0
```

**Comparison Testing:**
```python
def test_calculate_outcome_probabilities_strong_home():
    """Test that strong home team has higher win probability."""
    outcomes_home = calculate_outcome_probabilities(2.0, 0.8)
    outcomes_away = calculate_outcome_probabilities(0.8, 2.0)
    
    assert outcomes_home['home_win'] > outcomes_away['home_win']
```

**Invariant Testing:**
```python
def test_calculate_outcome_probabilities_sum():
    """Test that outcome probabilities sum to 1."""
    outcomes = calculate_outcome_probabilities(1.5, 1.2)
    
    total = outcomes['home_win'] + outcomes['draw'] + outcomes['away_win']
    assert total == pytest.approx(1.0, abs=0.001)
```

**Edge Case Testing:**
```python
def test_get_team_trailing_stats_empty():
    """Test trailing stats with no history."""
    stats = get_team_trailing_stats([], 8)
    
    assert stats['avg_gf'] is np.nan
    assert stats['matches'] == 0
```

## Async Testing

**Pattern:** Not used - codebase has no async functions

**Why:** All functions are synchronous, no I/O awaiting

## Error Testing

**Pattern:** Boundary value testing instead of exception testing

Example - Floating point edge case (lines 116-119):
```python
def test_poisson_probability_sum():
    """Test that Poisson probabilities sum to approximately 1."""
    total_prob = sum(poisson_probability(k, 1.5) for k in range(20))
    assert total_prob == pytest.approx(1.0, abs=0.001)
```

**What's NOT tested:**
- ValueError exceptions (not tested anywhere)
- FileNotFoundError exceptions (not tested)
- Data validation failures (not tested)

## Running Tests

**Quick Test:**
```bash
cd C:\Scripts\ML_Predictor2026_V2
pytest tests/test_main.py -v
```

**Test with Output:**
```bash
pytest tests/test_main.py -v -s
```

**Specific Test Category:**
```bash
# All Poisson tests
pytest tests/test_main.py -k "poisson" -v

# All Elo tests
pytest tests/test_main.py -k "elo" -v

# All normalization tests
pytest tests/test_main.py -k "normalize" -v
```

**From Python:**
```python
# tests/test_main.py line 359-360
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Test Execution Notes

**Current State:**
- Tests focus on mathematical correctness (Elo, Poisson, statistics)
- Strong coverage of core algorithms
- No integration/E2E tests for full pipeline
- No mocking means tests can't verify data loading behavior
- No model training tests

**Dependencies for Testing:**
- pytest >= 7.4.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- scipy >= 1.11.0
- All math libraries needed for functions being tested

**Test Execution Time:**
- Estimated: < 5 seconds (all tests are fast mathematical operations)
- No I/O delay
- No ML training in tests

## Test Quality Assessment

**Strengths:**
- ✅ Core algorithm correctness verified (Elo, Poisson math)
- ✅ Edge cases covered (empty data, boundary values)
- ✅ Invariant properties tested (probability sums to 1)
- ✅ Clear descriptive test names
- ✅ Good docstrings on every test
- ✅ Floating point comparison done correctly with pytest.approx()
- ✅ Random testing for robustness (test_calculate_expected_goals_bounds)

**Gaps:**
- ❌ No data loading tests (critical path untested)
- ❌ No model training/prediction tests
- ❌ No error handling verification
- ❌ No pipeline execution tests
- ❌ No file I/O validation
- ❌ No fixture/data integration tests
- ❌ No CSV parsing edge cases
- ❌ No JSON parsing edge cases

**Recommended Additions:**
1. Data processing tests with sample CSV/JSON files
2. Pipeline execution test with small historical dataset
3. Error handling tests for malformed data
4. Sofascore JSON parsing tests for multiple formats
5. Mock-based tests for external file dependencies
6. Model training/prediction tests

---

*Testing analysis: 2025-01-20*
