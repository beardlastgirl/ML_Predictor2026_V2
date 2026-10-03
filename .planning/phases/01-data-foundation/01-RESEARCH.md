# Phase 1: Data Foundation - Research

**Researched:** 2026-04-10
**Domain:** Betting odds integration, time-series leakage prevention
**Confidence:** HIGH

## Summary

This research covers two critical requirements for Milestone v2.0: (1) integrating betting odds as ML features and calibration baselines, and (2) preventing time-series leakage in feature engineering.

**Key findings:**
- ARG.csv already contains historical betting odds columns (PSC, Max, Avg, BFC, B365 prefixes) from Football-Data.co.uk
- Current pipeline uses `TimeSeriesSplit` but lacks explicit leakage validation
- Trailing features in `features.py` correctly use `shift(1)` to exclude current match
- Odds integration requires timestamp validation to prevent forward-looking bias

**Primary recommendation:** Extract and validate existing odds from ARG.csv, add temporal validation tests, implement odds-to-probability conversion for baseline comparison.

## User Constraints (from REQUIREMENTS.md)

### Locked Decisions
- DATA-01: Integrate betting odds as features and calibration baselines
  - Scrape historical odds from bookmakers
  - Add odds as ML model features
  - Use closing odds for model calibration baseline
- DATA-02: Improve data alignment and leakage prevention (time-series)
  - Validate chronological integrity of all features
  - Prevent look-ahead bias in trailing averages
  - Add time-series split validation tests

### Success Criteria
1. User can run pipeline with betting odds included as model features
2. User can verify no future data leaks in time-series splits (validation passes)
3. User can access closing odds for calibration baseline comparison

## Standard Stack

### Core (Existing - Do Not Change)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Python** | 3.8+ | Runtime | Project baseline |
| **Pandas** | 2.0.0 | Data manipulation | All data pipelines |
| **NumPy** | 1.24.0 | Numerical computation | Array operations |
| **scikit-learn** | 1.3.0 | ML utilities | TimeSeriesSplit, metrics |
| **CatBoost** | 1.2.0 | Primary ML model | Best performance |
| **LightGBM** | 4.0.0 | Secondary ML model | Alternative |

### New for Phase 1
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **odds-converter** | 1.0.0+ | Odds → implied probability | Lightweight, tested, single responsibility |
| **statsmodels** | 0.14.0+ | ADF stationarity tests | Industry standard for leakage detection |

### Installation
```bash
pip install odds-converter statsmodels
```

## Architecture Patterns

### Current Data Flow
```
ARG.csv (historical + odds) → data_processing.load_data()
                              ↓
                        apply_header_mapping() → canonical columns
                              ↓
                        features.compute_trailing_features() → shift(1) prevents leakage
                              ↓
                        stats_engine.calculate_poisson_features()
                              ↓
                        pipeline.train_validate() → TimeSeriesSplit CV
```

### Existing Odds Columns in ARG.csv
```csv
Country,League,Season,Date,Time,Home,Away,HG,AG,Res,PSCH,PSCD,PSCA,MaxCH,MaxCD,MaxCA,AvgCH,AvgCD,AvgCA,BFECH,BFECD,BFECA,B365CH,B365CD,B365CA
```

**Odds column patterns:**
- `PSCH/PSCD/PSCA` - Pinnacle Sports closing odds (Home/Draw/Away)
- `MaxCH/MaxCD/MaxCA` - Maximum market odds
- `AvgCH/AvgCD/AvgCA` - Average market odds
- `BFECH/BFECD/BFECA` - Betfair Exchange odds
- `B365CH/B365CD/B365CA` - Bet365 odds

### Recommended Project Structure (Additions)
```
src/
├── odds_engine.py          # NEW: Odds processing & probability conversion
├── validation.py           # NEW: Time-series leakage tests
└── data_processing.py      # MODIFY: Add odds column handling
```

## Pattern 1: Odds-to-Probability Conversion

**What:** Convert decimal odds to implied probabilities for ML features and baseline comparison.

**When to use:** Every match prediction, baseline model creation

**Example:**
```python
# Source: odds-converter PyPI
from odds_converter import decimal_to_implied_probability

def odds_to_probs(odds_home, odds_draw, odds_away):
    """Convert decimal odds to calibrated probabilities."""
    raw_probs = [
        1 / odds_home,
        1 / odds_draw,
        1 / odds_away
    ]
    # Normalize to sum to 1.0 (remove bookmaker margin)
    total = sum(raw_probs)
    return [p / total for p in raw_probs]

# Usage: closing_odds = df[['PSCH', 'PSCD', 'PSCA']].iloc[row]
# bookie_probs = odds_to_probs(*closing_odds)
```

## Pattern 2: Temporal Validation for Leakage

**What:** Verify all features use only data available BEFORE match date.

**When to use:** Before training, during CV fold creation

**Example:**
```python
# Source: machinelearningmastery.com time-series CV best practices
def validate_temporal_integrity(df, feature_cols, date_col='Date'):
    """Check for look-ahead bias in features."""
    df = df.sort_values(date_col).reset_index(drop=True)
    
    issues = []
    for col in feature_cols:
        # Check if feature correlates with future outcomes
        if col.endswith('_Avg_GF') or col.endswith('_Form'):
            # These should be lagged - verify shift(1) applied
            if not col.startswith('Home_') and not col.startswith('Away_'):
                issues.append(f"{col}: May include current match data")
    
    return issues

def check_cv_fold_independence(train_idx, test_idx, dates):
    """Verify no temporal overlap between CV folds."""
    train_dates = dates.iloc[train_idx]
    test_dates = dates.iloc[test_idx]
    
    assert train_dates.max() < test_dates.min(), "CV fold leakage detected!"
```

## Anti-Patterns to Avoid

- **Merging odds by match ID alone** — Always require timestamp validation (odds_timestamp < match_kickoff)
- **Using live/closing odds for training** — Only use opening odds for true pre-match baseline
- **Shuffling time-series data** — Never use `shuffle=True` in any split
- **Preprocessing before split** — Fit scalers on training fold only, not entire dataset

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Odds → probability | Manual formula with margin removal | `odds-converter` | Tested, handles edge cases, bookmaker-specific adjustments |
| ADF stationarity test | Custom implementation | `statsmodels.tsa.stattools.adfuller` | Peer-reviewed, industry standard |
| Time-series CV | Manual index splitting | `sklearn.TimeSeriesSplit` | Maintained, well-tested, integrates with sklearn pipeline |

**Key insight:** Odds math looks simple but has subtle bugs (margin calculation, draw probability adjustment). Use proven libraries.

## Common Pitfalls

### Pitfall 1: Forward-Looking Bias in Odds
**What goes wrong:** Odds scraped post-match contain information about the outcome. Using these as features teaches model to "predict" odds movement, not match outcomes.

**Why it happens:**
- ARG.csv contains closing odds (settled after match)
- No timestamp metadata to verify odds were available pre-match
- Merging by match ID alone loses temporal constraint

**How to avoid:**
- Document odds source: "closing odds" vs "opening odds"
- Add validation: `odds_timestamp < match_kickoff`
- For baseline: Use only opening odds (T-3 days before match)
- Add feature: `days_until_kickoff` to detect recency effects

**Warning signs:**
- Odds feature importance > 0.3 (model copying odds, not learning)
- Validation accuracy drops when moving to live predictions
- Model probabilities nearly identical to odds-implied probabilities

### Pitfall 2: Trailing Stats Include Current Match
**What goes wrong:** Computing trailing averages (last 8 matches) accidentally includes the current match, violating causality.

**Why it happens:**
- Loop through matches chronologically without resetting history
- Sofascore data scraped after matches (contains results), merged by team name only

**How to avoid:**
- Current `features.py` correctly uses `shift(1)` — verify this pattern continues
- Add unit test: For match N, verify trailing stats use only matches 0 to N-1
- Sofascore merge: Require `standings_date < match_date - 1 day`

**Warning signs:**
- Training accuracy > 50% on 3-class problem (suspiciously high)
- Feature importance shows trailing averages as top predictors

### Pitfall 3: CV Fold Contamination
**What goes wrong:** Test fold contains matches that occurred before training fold matches.

**Why it happens:**
- `TimeSeriesSplit` used but data not sorted by date first
- Multiple data sources merged without temporal alignment

**How to avoid:**
```python
# In pipeline.py:train_validate()
df = df.sort_values('Date').reset_index(drop=True)  # MUST do this BEFORE split
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(df):
    assert df.iloc[train_idx]['Date'].max() < df.iloc[test_idx]['Date'].min()
```

## Code Examples

### Extract Odds from ARG.csv
```python
# Source: Current ARG.csv structure
ODDS_COLUMNS = {
    'pinnacle': ['PSCH', 'PSCD', 'PSCA'],
    'max_market': ['MaxCH', 'MaxCD', 'MaxCA'],
    'avg_market': ['AvgCH', 'AvgCD', 'AvgCA'],
    'betfair': ['BFECH', 'BFECD', 'BFECA'],
    'bet365': ['B365CH', 'B365CD', 'B365CA'],
}

def extract_odds_features(df, bookmaker='pinnacle'):
    """Extract odds as ML features."""
    cols = ODDS_COLUMNS.get(bookmaker, ODDS_COLUMNS['pinnacle'])
    df = df.copy()
    df[f'{bookmaker}_home'] = df[cols[0]]
    df[f'{bookmaker}_draw'] = df[cols[1]]
    df[f'{bookmaker}_away'] = df[cols[2]]
    
    # Convert to implied probabilities
    df[f'{bookmaker}_prob_h'], df[f'{bookmaker}_prob_d'], df[f'{bookmaker}_prob_a'] = \
        zip(*df[cols].apply(lambda row: odds_to_probs(*row), axis=1))
    
    return df
```

### Create Bookmaker Baseline Model
```python
# Source: MODEL-01 requirement
def bookmaker_baseline(df, odds_col_prefix='PSC'):
    """Create baseline predictions from closing odds."""
    probs = []
    for _, row in df.iterrows():
        home, draw, away = odds_to_probs(
            row[f'{odds_col_prefix}H'],
            row[f'{odds_col_prefix}D'],
            row[f'{odds_col_prefix}A']
        )
        probs.append([home, draw, away])
    return np.array(probs)

# Compare: model_logloss vs bookie_logloss
```

### Leakage Validation Test
```python
# Source: sklearn TimeSeriesSplit best practices
def validate_no_leakage(df, feature_cols, date_col='Date'):
    """Run leakage checks before training."""
    from statsmodels.tsa.stattools import adfuller
    
    df = df.sort_values(date_col).reset_index(drop=True)
    issues = []
    
    # Check 1: Verify trailing features use shift(1)
    for col in feature_cols:
        if 'Avg' in col or 'Form' in col:
            # Spot-check: first non-null value should not use match 0 data
            first_valid_idx = df[col].first_valid_index()
            if first_valid_idx == 0:
                issues.append(f"{col}: First value should be NaN (no history)")
    
    # Check 2: ADF test on feature stability (detects non-stationarity)
    for col in feature_cols:
        if df[col].isna().sum() < len(df) * 0.5:  # Enough data
            stat, pvalue = adfuller(df[col].dropna(), autolag='AIC')[:2]
            if pvalue < 0.05:
                issues.append(f"{col}: Non-stationary (p={pvalue:.3f}) - possible leakage")
    
    return issues
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual odds → probability | `odds-converter` library | 2025 | Eliminates margin calculation bugs |
| Random K-fold CV | TimeSeriesSplit + gap | 2024 | Prevents temporal leakage |
| Season-wide Elo | Rolling Elo (last 38 matches) | 2025 | Adapts to team changes |
| Custom ADF test | `statsmodels` ADF | 2025 | Peer-reviewed implementation |

**Deprecated:**
- `shuffle=True` in any CV split — always use time-ordered splits
- Manual odds conversion without margin removal — use library

## Open Questions

1. **Which bookmaker odds to use as primary feature?**
   - Pinnacle (PSCH/PSCD/PSCA) typically sharpest
   - Average market odds may be more stable
   - Recommendation: Start with Pinnacle, ablate others

2. **Opening vs closing odds for baseline?**
   - Closing odds = market-efficient (harder to beat)
   - Opening odds = true pre-match (easier baseline)
   - Recommendation: Use closing for features, opening for baseline comparison

3. **How far back to fetch historical odds?**
   - ARG.csv has 2012-present (10+ seasons)
   - Recommendation: Use all available, validate by season

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.0+ |
| Config file | None (default pytest discovery) |
| Quick run command | `pytest tests/test_leakage.py -x -v` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DATA-01 | Odds as features | unit | `pytest tests/test_odds.py::test_odds_extraction -x` | ❌ Wave 0 |
| DATA-01 | Bookmaker baseline | integration | `pytest tests/test_baseline.py::test_bookie_comparison -x` | ❌ Wave 0 |
| DATA-02 | Temporal validation | unit | `pytest tests/test_leakage.py::test_temporal_integrity -x` | ❌ Wave 0 |
| DATA-02 | CV fold independence | unit | `pytest tests/test_leakage.py::test_cv_folds -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_*.py -x` (subset)
- **Per wave merge:** `pytest tests/ -x` (full suite)
- **Phase gate:** All leakage tests green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_odds.py` — odds extraction, probability conversion
- [ ] `tests/test_leakage.py` — temporal validation, CV fold checks
- [ ] `tests/test_baseline.py` — bookmaker baseline comparison
- [ ] `src/odds_engine.py` — new module for odds processing
- [ ] `src/validation.py` — new module for leakage tests

## Sources

### Primary (HIGH confidence)
- **ARG.csv data structure** — Verified columns: `PSCH,PSCD,PSCA,MaxCH,MaxCD,MaxCA,AvgCH,AvgCD,AvgCA,BFECH,BFECD,BFECA,B365CH,B365CD,B365CA`
- **Football-Data.co.uk** — https://www.football-data.co.uk/argentina.php (Argentina odds source)
- **Current features.py:68-70** — Uses `shift(1)` correctly for trailing averages
- **Current pipeline.py:263-266** — Uses `TimeSeriesSplit` for CV

### Secondary (MEDIUM confidence)
- **odds-converter PyPI** — https://pypi.org/project/odds-converter/ (v1.0.0+)
- **Time-series CV best practices** — https://machinelearningmastery.com/5-ways-to-use-cross-validation-to-improve-time-series-models/
- **Leakage prevention guide** — https://machinelearningmastery.com/3-subtle-ways-data-leakage-can-ruin-your-models-and-how-to-prevent-it/

### Tertiary (LOW confidence)
- **TheStatsAPI pricing** — £39/month (needs verification for live API option)
- **Pinnacle API reliability** — Reported issues since July 2025 (CSV data still valid)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Verified against existing requirements.txt and ARG.csv structure
- Architecture: HIGH — Based on current codebase patterns in features.py, pipeline.py
- Pitfalls: HIGH — Documented in existing .planning/research/PITFALLS.md, verified with web sources

**Research date:** 2026-04-10
**Valid until:** 30 days (stable domain — odds formats and CV patterns don't change rapidly)
