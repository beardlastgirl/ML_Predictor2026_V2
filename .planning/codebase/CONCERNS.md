# Codebase Concerns

**Analysis Date:** 2026-03-21

---

## 🔴 CRITICAL ISSUES (Must Fix Before Production)

### 1. Division by Zero in Form Calculation

**Issue:** Empty team history causes division by zero crash

**Files:** `src/features.py:30`

**Code:**
```python
form = points / len(recent)  # CRASHES if recent is empty
```

**Impact:** Pipeline immediately crashes for teams with sparse match history (no matches in trailing window). Results in complete pipeline failure and corrupted output files.

**Current Mitigation:** None

**Fix Approach:**
```python
form = points / len(recent) if recent else np.nan
```

**Priority:** CRITICAL - Blocks all pipelines with incomplete historical data

---

### 2. Integer Conversion Without Bounds Check

**Issue:** NaN/Inf values converted to int causing output corruption

**Files:** `src/pipeline.py:316`

**Code:**
```python
hg, ag = int(row["Pred_Home_Goals"]), int(row["Pred_Away_Goals"])
# NaN becomes error, Inf becomes system-dependent large value
```

**Impact:** Output file contains cryptic error messages or invalid goal counts. Silent data corruption that passes through to end users. Makes predictions uninterpretable.

**Current Mitigation:** None

**Fix Approach:**
```python
hg = int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6))
ag = int(np.clip(row.get("Pred_Away_Goals", 0), 0, 6))
```

**Priority:** CRITICAL - Results in unusable output files

---

### 3. Unsafe Probability Normalization

**Issue:** Division by zero possible in probability renormalization

**Files:** `src/stats_engine.py:107-110`

**Code:**
```python
total = p_home_win + p_draw_calibrated + p_away_win
p_home_win /= total        # CRASHES if total == 0
p_draw_calibrated /= total
p_away_win /= total
```

**Impact:** All probabilities become NaN/Inf, propagating through entire model output. Model becomes unusable for prediction. Silent cascade failure.

**Current Mitigation:** None

**Fix Approach:**
```python
total = p_home_win + p_draw_calibrated + p_away_win
if total > 1e-10:
    p_home_win /= total
    p_draw_calibrated /= total
    p_away_win /= total
else:
    # Edge case: fallback to uniform distribution
    p_home_win = p_draw_calibrated = p_away_win = 1/3
```

**Priority:** CRITICAL - Silently produces invalid models

---

## 🟠 HIGH-SEVERITY ISSUES (Fix Before Next Run)

### 4. Memory Leak in Pipeline Exception Handling

**Issue:** Matplotlib figures not closed on exceptions, accumulating memory

**Files:** `src/pipeline.py:294-306`

**Code:**
```python
plt.figure(figsize=(12, 8))
plt.barh(...)
plt.savefig(feature_importance_path, dpi=150)
plt.close()  # Only called if no exception before this line
```

**Impact:** After 10+ pipeline runs, Python process consumes 1-2GB+ RAM. Memory pressure causes subsequent runs to slow dramatically or OOM kill. Affects production schedulers running repeatedly.

**Current Mitigation:** None

**Fix Approach:**
```python
try:
    plt.figure(figsize=(12, 8))
    plt.barh(...)
    plt.savefig(feature_importance_path, dpi=150)
finally:
    plt.close()  # Always executes
```

**Priority:** HIGH - Degrades system over time

---

### 5. DataFrame Index Misalignment

**Issue:** Length mismatches in concat operations cause silent NaN columns

**Files:** `src/model_engine.py:74, 84`

**Code:**
```python
fixtures_df = pd.concat([fixtures_df, pd.DataFrame(team_stats_list, index=fixtures_df.index)], axis=1)
# If len(team_stats_list) != len(fixtures_df), index mismatch creates NaN
```

**Impact:** Features misaligned with fixture data → incorrect predictions mapped to wrong teams. Silent data corruption that produces plausible but wrong predictions.

**Current Mitigation:** None

**Fix Approach:**
```python
assert len(team_stats_list) == len(fixtures_df), f"Length mismatch: {len(team_stats_list)} vs {len(fixtures_df)}"
fixtures_df = pd.concat([fixtures_df, pd.DataFrame(team_stats_list, index=fixtures_df.index)], axis=1)
```

**Priority:** HIGH - Causes incorrect predictions

---

### 6. Unsafe String Method on NaN Data

**Issue:** `.upper()` called on NaN values in team name processing

**Files:** `src/model_engine.py:52-55`

**Code:**
```python
fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[side].apply(
    lambda x: sofascore_data.get(x.upper(), {}).get("position", 28)
)
# If fixtures_df[side] contains NaN, x.upper() throws AttributeError
```

**Impact:** Pipeline crashes when fixture data contains missing team names. AttributeError interrupts entire prediction run.

**Current Mitigation:** None

**Fix Approach:**
```python
def get_sofa_position(team_name):
    if pd.notna(team_name):
        return sofascore_data.get(team_name.upper(), {}).get("position", 28)
    return 28

fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[side].apply(get_sofa_position)
```

**Priority:** HIGH - Causes crashes with incomplete fixture data

---

### 7. Missing CSV Result Code Validation

**Issue:** Invalid result codes silently map to NaN without validation

**Files:** `src/pipeline.py:99`

**Code:**
```python
matches["Res"] = matches["Res"].map(RESULT_ENCODING)
# If "Res" contains unknown value like "3" or "Invalid", maps to NaN silently
```

**Impact:** Silent training data corruption. Unknown result codes become NaN, breaking model features and metrics. Training proceeds with corrupted data.

**Current Mitigation:** None

**Fix Approach:**
```python
invalid_codes = ~matches["Res"].isin(RESULT_ENCODING.keys())
if invalid_codes.any():
    log_warning(f"Found {invalid_codes.sum()} invalid result codes: {matches.loc[invalid_codes, 'Res'].unique()}")
matches["Res"] = matches["Res"].map(RESULT_ENCODING)
```

**Priority:** HIGH - Silent training data corruption

---

### 8. Scraper Resource Cleanup Missing

**Issue:** Browser sessions and file handles not closed on exception

**Files:** `scrape_sofascore_apify.py`, `scrape_stats_enhanced.py`, `scrape_sofascore.py`

**Code:**
```python
# Typical pattern: no cleanup on exception
page = browser.new_page()
# ... extraction code ...
browser.close()  # Only if no exception
```

**Impact:** Resource leaks accumulate. Open browser sessions consume memory. File handles remain locked preventing re-execution. System eventually refuses new connections.

**Current Mitigation:** None

**Fix Approach:**
```python
# Use context managers for all scrapers
from contextlib import contextmanager

@contextmanager
def managed_page(browser):
    page = browser.new_page()
    try:
        yield page
    finally:
        page.close()

# Usage
with managed_page(browser) as page:
    # extraction code
```

**Priority:** HIGH - Causes resource exhaustion on repeated runs

---

## 🟡 MEDIUM-SEVERITY ISSUES (Improve Reliability)

### 9. Draw Calibration Spread Across Multiple Files

**Issue:** Draw probability adjustment logic is fragmented and inconsistent

**Files:** `src/stats_engine.py:62-110` (primary), `src/model_engine.py:100-115` (secondary)

**Problem:** 
- Primary calibration in `calculate_outcome_probabilities()` applies `POISSON_DRAW_ADJUSTMENT`
- Secondary blending in `predict_gameweek()` applies additional ML ensemble mixing
- Configuration constant `POISSON_DRAW_ADJUSTMENT` is scattered across multiple code paths
- No single authority for how draws are calibrated

**Impact:** Inconsistent draw probabilities across training vs prediction. Difficult to debug calibration issues. Changing draw bias requires modifications in multiple locations.

**Fix Approach:**
1. Centralize draw calibration logic in single function `calibrate_match_probabilities()`
2. Create config class `DrawCalibrationConfig` with all parameters
3. Call single calibration function from both training and prediction paths

**Priority:** MEDIUM - Currently works but fragile to future changes

---

### 10. Team Name Normalization Duplicated Across Files

**Issue:** Team name normalization logic duplicated in multiple scrapers

**Files:**
- `src/data_processing.py:39-61` (main normalization)
- `scrape_sofascore_apify.py:35-79` (duplicate mappings)
- `scrape_sofascore.py` (uses data_processing version)
- `src/model_engine.py:52` (inline normalization)

**Code:**
```python
# scrape_sofascore_apify.py has hardcoded mappings:
mappings = {
    "Boca Juniors": "BOCA JUNIORS",
    "River Plate": "RIVER PLATE",
    # ... 25+ more mappings
}

# But src/data_processing.py has glossary.txt approach
```

**Impact:** When glossary.txt is updated, scraper mappings become stale. Creates team name mismatches between data sources. Maintenance burden doubles with each new team.

**Fix Approach:**
```python
# Consolidate in data_processing.py
from src.data_processing import normalize_team_name

# All scrapers use single source:
normalized = normalize_team_name(name, glossary)
```

**Priority:** MEDIUM - Maintenance burden, inconsistency risk

---

### 11. Numeric Edge Cases in Expected Goals Calculation

**Issue:** Extreme Elo differences produce unbounded xG values

**Files:** `src/stats_engine.py:44-56`

**Code:**
```python
elo_diff = elo_home - elo_away
elo_factor = 1 + (elo_diff / ELO_FACTOR_DENOM)

xG_home = xG_home * elo_factor  # Can explode with large elo_diff
xG_away = xG_away / elo_factor

# Clipping happens after multiplication
xG_home = max(XG_MIN, min(XG_MAX, xG_home))  # Bounds: 0.2 to 4.0
```

**Problem:**
- With Elo diff of 500: `elo_factor = 1 + (500/20) = 26`
- `xG_home = 1.5 * 26 = 39` → clipped to 4.0 (valid but misleading)
- Very strong teams lose all predictive power

**Impact:** Extreme team matchups (e.g., top vs relegated) produce unrealistic goal expectations. Model can't differentiate within bounds.

**Fix Approach:**
```python
# Clip elo_factor before using
elo_factor = np.clip(1 + (elo_diff / ELO_FACTOR_DENOM), 0.5, 2.0)
xG_home = np.clip(xG_home * elo_factor, XG_MIN, XG_MAX)
xG_away = np.clip(xG_away / elo_factor, XG_MIN, XG_MAX)
```

**Priority:** MEDIUM - Affects edge case matches

---

### 12. Test Coverage Gaps for Edge Cases

**Issue:** Critical edge cases not covered by test suite

**Files:** `tests/test_main.py` (86 tests but missing key scenarios)

**Missing Test Coverage:**
1. Division by zero edge cases (empty history, zero probabilities)
2. NaN/Inf propagation through pipeline
3. Empty DataFrame handling in model
4. Extreme Elo differences (1000+ gap)
5. Missing team names in fixtures vs historical data
6. Invalid result codes
7. Mismatched DataFrame lengths

**Example Gap:**
```python
# Tests exist for normal case:
def test_get_team_trailing_stats_window_limit():
    history = [...]
    stats = get_team_trailing_stats(history, 3)
    assert stats['matches'] == 3

# But NOT for edge case:
# What if recent = []? Current: form = points / 0 → CRASH
# Test should catch this:
def test_get_team_trailing_stats_empty_recent_MISSING():
    history = []
    stats = get_team_trailing_stats(history, 8)
    assert stats['form'] is np.nan  # Should not crash
```

**Impact:** Edge cases silently crash in production but pass test suite.

**Fix Approach:**
Add 12+ test cases covering:
- All division-by-zero paths
- NaN/Inf handling
- Empty collections
- Type mismatches
- Extreme values

**Priority:** MEDIUM - High risk, easily fixable

---

### 13. Bare Exception Handlers Masking Errors

**Issue:** Broad `except Exception` clauses hide root causes

**Files:**
- `scrape_sofascore.py:101-102` - Bare `except: continue`
- `src/data_processing.py:35-36` - `except Exception: log_error`
- `src/pipeline.py:102-104` - `except Exception: raise` (ok, but loses context)

**Code:**
```python
# scrape_sofascore.py:101
except Exception:
    continue  # What went wrong? Unknown.

# src/data_processing.py:35
except Exception as e:
    log_error(f"Error reading glossary: {e}")
    # Lost stack trace, swallows real problem
```

**Impact:** When bugs occur, logs don't show stack traces or context. Debugging requires attaching debuggers or adding temporary print statements. Production issues take hours to diagnose.

**Fix Approach:**
```python
except Exception as e:
    log_error(f"Error reading glossary: {e}", exc_info=True)  # Include traceback
    raise  # Let caller handle, don't silently continue
```

**Priority:** MEDIUM - Maintenance and debugging burden

---

## 🟢 SECURITY & STABILITY CONSIDERATIONS

### 14. Subprocess Execution Without Path Validation

**Issue:** Chrome path not validated before subprocess execution

**Files:** `scrape_stats_manual.py:56`

**Code:**
```python
subprocess.run([chrome_path, "--remote-debugging-port=9222"])
# chrome_path might be from user input or environment variable
```

**Risk:** Low risk (input is typically from os.getenv or hardcoded paths), but violates security practice. If chrome_path comes from untrusted source, could execute arbitrary commands.

**Fix Approach:**
```python
# Validate path exists and is executable
if not os.path.exists(chrome_path):
    raise ValueError(f"Chrome not found: {chrome_path}")
if not os.access(chrome_path, os.X_OK):
    raise ValueError(f"Chrome not executable: {chrome_path}")

subprocess.run([chrome_path, "--remote-debugging-port=9222"])
```

**Priority:** MEDIUM - Low immediate risk but good practice

---

### 15. CSV Injection Risk in Output

**Issue:** Team names written directly to CSV without sanitization

**Files:** `src/pipeline.py:318-322`

**Code:**
```python
f.write(f"{row.get('Raw_Home', row['Home'])} - {row.get('Raw_Away', row['Away'])}\n")
# If Home team name starts with "=", could be interpreted as formula
```

**Risk:** LOW - Output is TXT not CSV, but practices matter. If future refactoring writes to CSV, this becomes HIGH risk. Pandas is safe by default but explicit defense is better.

**Fix Approach:**
```python
def sanitize_for_csv(value):
    """Prevent formula injection."""
    if isinstance(value, str) and value[0] in ['=', '+', '-', '@']:
        return "'" + value  # Quote the formula
    return value

home_name = sanitize_for_csv(row.get('Raw_Home', row['Home']))
f.write(f"{home_name} - {away_name}\n")
```

**Priority:** MEDIUM - Defensive practice

---

## 📊 PERFORMANCE & SCALING

### 16. DataFrame Operations Not Optimized for Scale

**Issue:** Multiple iterrows() loops and concat operations on large DataFrames

**Files:**
- `src/pipeline.py:153-166` - Poisson features calculated row-by-row
- `src/model_engine.py:77-84` - Same pattern in prediction

**Code:**
```python
# SLOW: Row-by-row operation
poisson_features = [
    calculate_poisson_features(r["Home_Elo"], r["Away_Elo"], ...)
    for _, r in matches.iterrows()
]
```

**Impact:** With 1000+ historical matches:
- Row-by-row iteration: ~2-3 seconds
- Vectorized operation: ~0.2 seconds
- 10-15x slower than necessary

**Fix Approach:**
```python
# FAST: Vectorized operation
home_elo = matches["Home_Elo"].values
away_elo = matches["Away_Elo"].values
# Call vectorized function
poisson_features = calculate_poisson_features_vectorized(home_elo, away_elo, ...)
```

**Priority:** MEDIUM - Affects production runtime but not critical

---

### 17. No Caching for Repeated Computations

**Issue:** Elo ratings recalculated on every pipeline run despite being stable

**Files:** `src/stats_engine.py:146-173` (calculate_all_elo_ratings)

**Problem:** Complete Elo history recalculated from scratch every run. For 2000+ historical matches, reprocessing adds 1-2 seconds per run unnecessarily.

**Fix Approach:**
```python
# Cache last known elo ratings + timestamp
# Only recalculate if new matches added since last run
@functools.lru_cache(maxsize=1)
def calculate_all_elo_ratings_cached(matches_hash, base_elo=BASE_ELO):
    # ...
```

**Priority:** MEDIUM - Nice-to-have optimization

---

## 📋 MAINTENANCE BURDEN

### 18. Hardcoded Magic Numbers Scattered Across Codebase

**Issue:** Configuration values hardcoded in functions rather than centralized

**Files:**
- `src/stats_engine.py:102` - `home_advantage_boost = 0.08` (should be config)
- `src/model_engine.py:67-72` - Default values hardcoded (1.0, 0.5)
- `scrape_sofascore_apify.py:45-73` - Team mappings hardcoded

**Impact:** Tuning model requires editing multiple files. Easy to miss one. Introduces bugs.

**Fix Approach:**
Create `src/magic_numbers.py`:
```python
# All configuration in one place
HOME_ADVANTAGE_BOOST = 0.08
DEFAULT_AVG_GF = 1.0
DEFAULT_FORM = 0.5
```

**Priority:** LOW - Code quality issue

---

### 19. Missing Type Hints on Critical Functions

**Issue:** Core functions lack type hints, making IDE navigation difficult

**Files:**
- `src/features.py:7` - No return type on `get_team_trailing_stats()`
- `src/stats_engine.py:14` - No type hints
- `src/pipeline.py:65` - Function signature incomplete

**Impact:** IDE can't auto-complete. Runtime type errors not caught. Refactoring unsafe.

**Fix Approach:**
```python
from typing import Dict, List, Optional

def get_team_trailing_stats(
    history: List[Dict[str, float]], 
    window: int
) -> Dict[str, float]:
    """Calculate trailing statistics from team history."""
```

**Priority:** LOW - Code quality, aids maintenance

---

## 🔍 ROOT CAUSE ANALYSIS

### Pattern: Numeric Boundary Conditions

**Common Theme:** Division by zero, NaN propagation, Inf handling

**Root Cause:** 
1. Limited input validation at data boundaries
2. No explicit handling for edge cases (empty collections, zero denominators)
3. Relying on implicit NumPy behavior rather than explicit checks

**Systemic Fix:**
```python
# Pattern: Always validate before division
def safe_divide(numerator, denominator, default=np.nan):
    if denominator == 0 or denominator < 1e-10:
        return default
    return numerator / denominator
```

---

### Pattern: Resource Management

**Common Theme:** Files/figures/connections not closed on exceptions

**Root Cause:**
1. Using procedural try/except rather than context managers
2. Cleanup logic at end of try block (only runs if no exception)
3. No structured approach to resource lifecycle

**Systemic Fix:**
```python
# Always use context managers
with managed_resource() as resource:
    # Use resource
    # Guaranteed cleanup even on exception
```

---

### Pattern: Data Normalization Duplication

**Common Theme:** Same logic in multiple scrapers

**Root Cause:**
1. Each scraper developed independently
2. No centralized data normalization layer
3. Scrapers not using shared utilities

**Systemic Fix:**
```python
# Create scraper base class
class BaseScraper:
    def normalize_name(self, name):
        return normalize_team_name(name, self.glossary)
```

---

## 📈 PRIORITY ROADMAP

### Phase 1: CRITICAL (Week 1 - Production Blocking)
1. Fix division by zero in form calculation
2. Fix integer conversion bounds
3. Fix probability normalization
4. Add comprehensive edge case tests

**Estimated effort:** 4-6 hours

---

### Phase 2: HIGH (Week 2 - Reliability)
4. Fix matplotlib memory leak
5. Add DataFrame alignment assertions
6. Fix NaN handling in sofascore features
7. Add CSV result code validation
8. Implement scraper resource cleanup

**Estimated effort:** 8-10 hours

---

### Phase 3: MEDIUM (Week 3-4 - Robustness)
9. Centralize draw calibration logic
10. Consolidate team name normalization
11. Add bounds checking to Elo factor
12. Expand test coverage
13. Improve exception handling with context

**Estimated effort:** 12-15 hours

---

### Phase 4: NICE-TO-HAVE (Ongoing)
14. Validate subprocess paths
15. Sanitize CSV output
16. Optimize DataFrame operations
17. Add caching layer
18. Add type hints
19. Centralize magic numbers

---

## Summary Statistics

| Category | Count | Severity |
|----------|-------|----------|
| Critical Bugs | 3 | 🔴 Must fix immediately |
| High-Priority Issues | 5 | 🟠 Fix before next run |
| Medium Issues | 11 | 🟡 Plan for next sprint |
| Low Issues | 4 | 🟢 Maintenance debt |
| **Total Concerns** | **23** | Requires ~40 hours to fully remediate |

---

*Concerns audit: 2026-03-21 | Based on CODE_REVIEW_2026_03_21.md + codebase exploration*
