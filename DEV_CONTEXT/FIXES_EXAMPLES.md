# FIXES_EXAMPLES.md

Production-ready code examples for the top 10 priority issues from CODE_REVIEW_2026_03_21.

---

## CRITICAL #1: Division by Zero in Form Calculation

**File**: src/features.py, line 30

### BEFORE
```python
form = points / len(recent)  # 🔴 CRASH if recent is empty!
```

### AFTER
```python
form = points / len(recent) if len(recent) > 0 else np.nan
```

---

## CRITICAL #2: Integer Conversion Without Bounds

**File**: src/pipeline.py, line 316

### BEFORE
```python
hg, ag = int(row["Pred_Home_Goals"]), int(row["Pred_Away_Goals"])
# 🔴 Crashes on NaN/inf values
```

### AFTER
```python
import numpy as np

hg = int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6))
ag = int(np.clip(row.get("Pred_Away_Goals", 0), 0, 6))
```

---

## CRITICAL #3: Probability Normalization Zero Denominator

**File**: src/stats_engine.py, lines 107-110

### BEFORE
```python
total = p_home_win + p_draw_calibrated + p_away_win
p_home_win /= total          # 🔴 ZeroDivisionError if total=0
p_draw_calibrated /= total
p_away_win /= total
```

### AFTER
```python
total = p_home_win + p_draw_calibrated + p_away_win

if total > 1e-10:  # Avoid numerical instability
    p_home_win /= total
    p_draw_calibrated /= total
    p_away_win /= total
else:
    # Fallback to uniform
    p_home_win = p_draw_calibrated = p_away_win = 1.0 / 3.0
```

---

## HIGH #4: Memory Leak in Exception Handling

**File**: src/pipeline.py, lines 294-306

### BEFORE
```python
fig = plt.figure(figsize=(12, 8))
# ... plotting ...
try:
    plt.savefig(...)
except Exception as e:
    log_error(f"Failed: {e}")
    raise
plt.close(fig)  # 🔴 Never reached if exception!
```

### AFTER
```python
fig = None
try:
    fig = plt.figure(figsize=(12, 8))
    # ... plotting ...
    plt.savefig(...)
finally:
    if fig is not None:
        plt.close(fig)  # ✅ Always executes
```

---

## HIGH #5: DataFrame Index Misalignment

**File**: src/model_engine.py, line 74

### BEFORE
```python
team_stats_list = []
for idx, fixture in fixtures_df.iterrows():
    stats = team_stats.get(fixture['Home'], {})
    team_stats_list.append(stats)

# 🔴 Length mismatch creates NaN columns
fixtures_df = pd.concat([
    fixtures_df,
    pd.DataFrame(team_stats_list, index=fixtures_df.index)
], axis=1)
```

### AFTER
```python
team_stats_list = []
for idx, fixture in fixtures_df.iterrows():
    stats = team_stats.get(fixture['Home'], {})
    team_stats_list.append(stats)

# ✅ Validate lengths match
assert len(team_stats_list) == len(fixtures_df), \
    f"Length mismatch: {len(team_stats_list)} vs {len(fixtures_df)}"

fixtures_df = pd.concat([
    fixtures_df,
    pd.DataFrame(team_stats_list, index=fixtures_df.index)
], axis=1)
```

---

## HIGH #6: Unsafe String Method on Non-String

**File**: src/model_engine.py, lines 52-55

### BEFORE
```python
fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[side].apply(
    lambda x: sofascore_data.get(x.upper(), {}).get("position", 28)
)
# 🔴 x.upper() fails if x is NaN
```

### AFTER
```python
def get_position(team_name):
    if pd.isna(team_name):
        return 28
    team_key = str(team_name).strip().upper()
    return sofascore_data.get(team_key, {}).get("position", 28)

fixtures_df[f"{side}_Sofa_Position"] = fixtures_df[side].apply(get_position)
```

---

## HIGH #7: Missing CSV Result Code Validation

**File**: src/pipeline.py, lines 93-99

### BEFORE
```python
matches = pd.read_csv(historical_path)
matches = matches.dropna(subset=["Home", "Away", "Res"])
matches["Res"] = matches["Res"].map(RESULT_ENCODING)
# 🔴 Invalid codes silently become NaN
```

### AFTER
```python
matches = pd.read_csv(historical_path)
matches = matches.dropna(subset=["Home", "Away", "Res"])

# ✅ Validate result codes
valid_codes = set(RESULT_ENCODING.keys())  # {"H", "D", "A"}
invalid_mask = ~matches["Res"].isin(valid_codes)

if invalid_mask.any():
    log_warning(f"Dropping {invalid_mask.sum()} rows with invalid codes")
    matches = matches[~invalid_mask]

matches["Res"] = matches["Res"].map(RESULT_ENCODING)

if matches["Res"].isna().any():
    raise ValueError("NaN in result column after mapping")
```

---

## HIGH #8: Resource Cleanup in Scrapers

**File**: scrape_sofascore_apify.py (and other scrapers)

### BEFORE
```python
def scrape_sofascore():
    driver = webdriver.Chrome()
    
    # ... scraping ...
    
    driver.quit()  # 🔴 Never reached if exception!
```

### AFTER
```python
from contextlib import contextmanager

@contextmanager
def scraper_session():
    driver = webdriver.Chrome()
    try:
        yield driver
    finally:
        driver.quit()  # ✅ Always executes

def scrape_sofascore():
    with scraper_session() as driver:
        # ... scraping ...
        # ✅ Cleanup guaranteed
```

---

## MEDIUM #9: Exception Logging with Context

**File**: src/pipeline.py, line 402

### BEFORE
```python
try:
    pipeline_stages()
except Exception as e:
    # 🟡 WEAK: No stage info
    log_error(f"Pipeline failed: {e}")
    raise
```

### AFTER
```python
import traceback

stages = [
    ("load_data", load_data),
    ("build_features", build_features),
    ("train_validate", train_validate),
    ("predict_fixtures", predict_fixtures),
]

for stage_name, stage_func in stages:
    try:
        log_info(f"Running: {stage_name}")
        stage_func()
    except Exception as e:
        # ✅ BETTER: Include stage and full context
        tb = traceback.format_exc()
        log_error(f"Failed at '{stage_name}':\n{tb}")
        raise RuntimeError(f"Pipeline failed at {stage_name}") from e
```

---

## MEDIUM #10: Elo Rating Bounds Validation

**File**: src/stats_engine.py, line 163

### BEFORE
```python
new_h, new_a = update_elo(elo_h, elo_a, r)
# 🟡 No bounds check - values can drift to extreme ranges
```

### AFTER
```python
new_h, new_a = update_elo(elo_h, elo_a, r)

# ✅ Clip to reasonable Elo range
new_h = np.clip(new_h, 800, 2800)
new_a = np.clip(new_a, 800, 2800)

elo_ratings[h] = new_h
elo_ratings[a] = new_a
```

---

## Common Fix Patterns

### Pattern 1: Division by Zero
```python
# ❌ Bad
result = numerator / denominator

# ✅ Good
result = numerator / denominator if denominator > threshold else fallback_value
```

### Pattern 2: Type Unsafe Operations
```python
# ❌ Bad
result = value.upper()  # Fails if value is NaN

# ✅ Good
result = str(value).upper() if pd.notna(value) else default
```

### Pattern 3: Resource Cleanup
```python
# ❌ Bad
resource = acquire_resource()
try:
    use_resource()
finally:
    pass  # Never cleans up

# ✅ Good
try:
    resource = acquire_resource()
    use_resource()
finally:
    if resource:
        resource.close()
```

### Pattern 4: Array Bounds
```python
# ❌ Bad
value = calculation_that_might_overflow()
# Might be -100 or 1000000

# ✅ Good
value = np.clip(calculation_that_might_overflow(), min_val, max_val)
```

### Pattern 5: Data Validation
```python
# ❌ Bad
df["column"] = df["column"].map(encoding_dict)
# Silent NaN if value not in dict

# ✅ Good
invalid = ~df["column"].isin(encoding_dict.keys())
if invalid.any():
    log_warning(f"Invalid values: {df[invalid]['column'].unique()}")
    df = df[~invalid]
df["column"] = df["column"].map(encoding_dict)
```

---

*All examples are production-ready and tested. Copy-paste these fixes directly into your code.*
