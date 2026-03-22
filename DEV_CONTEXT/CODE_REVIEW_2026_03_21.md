# CODE_REVIEW_2026_03_21.md

**Date**: 2026-03-21  
**Reviewer**: Copilot CLI  
**Total Issues**: 29 (3 critical, 5 high, 12 medium, 9 low)  
**Code Quality Score**: 6.5/10

---

## Executive Summary

The codebase is generally well-structured with proper module separation, but contains **critical numeric edge cases** and **missing error handling** that could cause silent failures or data corruption. Most issues relate to:
- Numeric boundary conditions (division by zero, NaN/Inf handling)
- Data validation and type conversions
- Resource management (memory leaks)
- Exception handling (bare excepts, missing context)

**Recommendation**: Address all critical and high-severity issues before next production deployment.

---

## 🔴 CRITICAL ISSUES (3)

### 1. Division by Zero in Form Calculation
- **File**: `src/features.py`, line 30
- **Issue**: `form = points / len(recent)` crashes if recent list is empty
- **Impact**: Pipeline crash for teams with sparse match history
- **Fix**:
```python
form = points / len(recent) if recent else np.nan
```

### 2. Integer Conversion Without Bounds Check
- **File**: `src/pipeline.py`, line 316
- **Issue**: No validation of NaN/inf values before int() conversion
- **Impact**: Output file corruption with cryptic errors
- **Fix**:
```python
hg = int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6))
ag = int(np.clip(row.get("Pred_Away_Goals", 0), 0, 6))
```

### 3. Unsafe Probability Normalization
- **File**: `src/stats_engine.py`, lines 107-110
- **Issue**: Division by zero possible if total = 0
- **Impact**: All probabilities become NaN/Inf
- **Fix**:
```python
if total > 1e-10:
    p_home_win /= total
    p_draw_calibrated /= total
    p_away_win /= total
else:
    p_home_win = p_draw_calibrated = p_away_win = 1/3
```

---

## 🟠 HIGH-SEVERITY ISSUES (5)

### 4. Memory Leak in Pipeline Exception Handling
- **File**: `src/pipeline.py`, lines 294-306
- **Issue**: Matplotlib figures not closed if exception occurs before cleanup
- **Impact**: Memory exhaustion after multiple pipeline runs
- **Fix**: Use try-finally to ensure plt.close() always executes

### 5. DataFrame Index Misalignment
- **File**: `src/model_engine.py`, lines 74 & 84
- **Issue**: Length mismatches in concat cause silent NaN columns
- **Impact**: Features misaligned with fixture data → incorrect predictions
- **Fix**: Assert lengths match before concatenation

### 6. Unsafe String Method on Non-String Data
- **File**: `src/model_engine.py`, lines 52-55
- **Issue**: `.upper()` called on potentially NaN values
- **Impact**: AttributeError when team names are NaN
- **Fix**: Check `pd.notna(x)` before .upper()

### 7. Missing CSV Result Code Validation
- **File**: `src/pipeline.py`, lines 93-99
- **Issue**: Invalid result codes silently map to NaN
- **Impact**: Silent training data corruption
- **Fix**: Validate against RESULT_ENCODING keys before mapping

### 8. Resource Cleanup Missing in Scrapers
- **File**: scrape_sofascore_apify.py, scrape_stats_enhanced.py
- **Issue**: Browser sessions/drivers not closed on exception
- **Impact**: Resource leaks, open file handles
- **Fix**: Use context managers for all web scrapers

---

## 🟡 MEDIUM-SEVERITY ISSUES (12)

1. Bare exception with silent failure - scrape_sofascore.py:101
2. Incomplete numeric type conversion - scrape_sofascore.py:88-90
3. Missing goal prediction bounds - model_engine.py:145-154
4. Generic exception context in pipeline - pipeline.py:402
5. Missing glossary empty check - pipeline.py:84
6. Unsafe NumPy array division - stats_engine.py:181
7. No Elo bounds validation - stats_engine.py:163
8. XG calculation produces extreme values - stats_engine.py:48-51
9. Division by zero in summary report - main.py:22
10. Feature importance without type check - pipeline.py:376
11. CV accuracy calculation without empty check - pipeline.py:376
12. Test coverage missing for edge cases - tests/test_main.py

---

## 🟢 LOW-SEVERITY ISSUES (9)

- Code duplication in team normalization
- Hardcoded magic numbers across files
- Missing type hints on core functions
- Inconsistent error message formatting
- Input validation gaps in utility functions
- Multiple bare print statements mixed with logging
- No bounds validation on streaming inputs
- Missing docstrings on complex functions
- Incomplete error recovery paths

---

## 🔐 SECURITY ISSUES (2)

1. **Subprocess Execution Without Path Validation** (scrape_stats_manual.py:56)
   - Chrome path not validated before execution
   - Low risk but poor security practice

2. **CSV Injection Risk** (src/pipeline.py:93)
   - Low risk (Pandas is safe), but add dataset size sanity checks

---

## 📋 PRIORITY FIX ORDER

| # | Issue | File | Severity | Impact |
|---|-------|------|----------|--------|
| 1 | Division by zero in form | src/features.py:30 | 🔴 | Pipeline crash |
| 2 | Integer conversion bounds | src/pipeline.py:316 | 🔴 | Output corruption |
| 3 | Probability normalization | src/stats_engine.py:107 | 🔴 | NaN/Inf propagation |
| 4 | Matplotlib memory leak | src/pipeline.py:294 | 🟠 | Memory exhaustion |
| 5 | DataFrame alignment | src/model_engine.py:74 | 🟠 | Incorrect predictions |
| 6 | String method safety | src/model_engine.py:52 | 🟠 | Pipeline crash |
| 7 | CSV validation | src/pipeline.py:99 | 🟠 | Silent corruption |
| 8 | Scraper cleanup | scrape_sofascore_apify.py | 🟠 | Resource leak |
| 9 | Exception logging | src/pipeline.py:402 | 🟡 | Debug difficulty |
| 10 | Elo bounds | src/stats_engine.py:163 | 🟡 | Numerical instability |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Bugs | 14 |
| Code Quality | 12 |
| Security | 2 |
| Test Gaps | 1 |
| **Total** | **29** |

---

## Files Referenced

- src/features.py - Form calculation
- src/pipeline.py - Main orchestration, data loading, output writing
- src/stats_engine.py - Elo/Poisson math
- src/model_engine.py - ML model and prediction
- src/data_processing.py - Data normalization
- scrape_sofascore_apify.py - Web scraping
- scrape_sofascore.py - Table parsing
- scrape_stats_enhanced.py - FBref scraper
- scrape_stats_manual.py - Manual browser scraper
- tests/test_main.py - Test suite
- main.py - Entry point

---

*See FIXES_EXAMPLES.md for before/after code for the top 10 issues.*
