# Architecture: v2.0 Feature Integration

**Project:** ML_Predictor2026_V2  
**Researched:** 2026-03-22  
**Focus:** How do betting odds, time-series leakage prevention, Poisson calibration, baseline models, and Coordinator-Worker patterns integrate into the existing architecture?

---

## Current Architecture (v1.0)

```
[Scrapers: FBref, TyC, Sofascore]
    |  (write CSV/JSON/TXT)
    v
[Data files: data/ARG.csv, partidos.txt, src/sofascore_stats.json]
    |
    v
[load_data()] → normalize teams + parse fixtures
    |
    v
[build_features()] → Elo + trailing stats + Poisson + Shin odds probabilities
    |
    v
[train_validate()] → TimeSeriesSplit CV + CatBoost training
    |
    v
[predict_fixtures()] → ML + Poisson probability blend (60/40) + scoreline generation
    |
    v
[write_outputs()] → Resultados_YYYYMMDD.txt + feature_importance.png
```

**Key components:**
- `src/pipeline.py`: Orchestrator (sequential, synchronous)
- `src/model_engine.py`: Model training and prediction
- `src/stats_engine.py`: Elo + Poisson math
- `src/features.py`: Trailing statistics
- `src/data_processing.py`: Normalization, input parsing

**Data flow:** File → Normalize → Feature → Train → Predict → Output

---

## Recommended v2.0 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES (NEW)                      │
│  - OddsAPI / Betfair / Pinnacle (betting odds)                      │
│  - Optional: Real-time league standings scraper                     │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│              DATA INGESTION & VALIDATION LAYER (NEW)                │
│                                                                      │
│  odds_pipeline.py (NEW)                                             │
│  ├─ fetch_odds() → normalize implied probabilities                  │
│  ├─ validate_odds() → check data quality, freshness               │
│  └─ cache_odds() → local storage for historical reference           │
│                                                                      │
│  data_processing.py (EXTENDED)                                      │
│  ├─ load_odds_source() (NEW)                                        │
│  └─ [existing] normalize_team_name(), load_sofascore_data()        │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│                  FEATURE ENGINEERING PIPELINE                       │
│                                                                      │
│  features.py (EXTENDED)                                             │
│  ├─ compute_trailing_features()   (existing)                        │
│  ├─ compute_odds_features() (NEW)  → implied probs from odds        │
│  └─ calibration_indicators() (NEW) → external data for baseline     │
│                                                                      │
│  stats_engine.py (EXTENDED)                                         │
│  ├─ calculate_poisson_features()   (existing)                       │
│  ├─ calculate_poisson_calibration() (NEW) → compare vs. realized   │
│  └─ shin_method()                  (existing, enhanced with odds)   │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│              TIME-SERIES VALIDATION LAYER (NEW)                     │
│                                                                      │
│  validation.py (NEW)                                                │
│  ├─ check_data_leakage() → verify feature cutoff dates             │
│  ├─ temporal_split_cv() → enhanced TimeSeriesSplit with bounds     │
│  ├─ stationarity_check() → ADF test for Elo/form series            │
│  └─ feature_forward_check() → ensure no future data in features    │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│               MODEL TRAINING & BASELINE COMPARISON                  │
│                                                                      │
│  model_registry.py (NEW)                                            │
│  ├─ Baseline: LogisticRegression (odds-only model)                  │
│  ├─ Baseline: Odds-as-prediction (bookie probabilities)             │
│  ├─ Primary: CatBoost (existing)                                    │
│  ├─ Secondary: LightGBM (existing)                                  │
│  └─ Ensemble: Weighted blend of CatBoost + Baseline                │
│                                                                      │
│  model_engine.py (EXTENDED)                                         │
│  ├─ train_baseline_models() (NEW)                                   │
│  ├─ compare_models() (NEW) → metrics for each candidate             │
│  └─ select_best_model() (NEW) → choose winner based on CV           │
│                                                                      │
│  pipeline.py (MODIFIED)                                             │
│  └─ train_validate() → call validation layer before CV              │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│            POISSON CALIBRATION VERIFIER (NEW)                       │
│                                                                      │
│  calibration.py (NEW)                                               │
│  ├─ calibration_metrics() → Expected Calibration Error (ECE)        │
│  ├─ compare_poisson_vs_realized() → how well does Poisson fit?      │
│  ├─ calibration_plot() → visualization of predicted vs. actual      │
│  └─ suggest_parameter_adjustments() → tuning recommendations        │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│            PREDICTION ENGINE & COORDINATOR-WORKER (NEW)             │
│                                                                      │
│  coordinator.py (NEW)                                               │
│  ├─ TaskQueue: coordinate_prediction_batch(fixtures_list)           │
│  ├─ Workers: worker_predict_fixture(fixture) [parallel]             │
│  ├─ Aggregation: aggregate_predictions(worker_results)              │
│  └─ Retry logic: handle failed prediction tasks                     │
│                                                                      │
│  model_engine.py (EXTENDED)                                         │
│  └─ predict_gameweek() → now called by worker task                  │
└─────────────────────────────────────────────────────────────────────┘
                                |
                                v
┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT & REPORTING                          │
│                                                                      │
│  output.py (EXTENDED)                                               │
│  ├─ Resultados_YYYYMMDD.txt (existing format)                       │
│  ├─ calibration_report.txt (NEW) → Poisson vs. realized stats       │
│  ├─ baseline_comparison.txt (NEW) → model performance comparison    │
│  ├─ feature_importance_YYYYMMDD.png (existing)                      │
│  └─ odds_implied_vs_predicted.csv (NEW) → calibration data          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Input | Output | Communicates With |
|-----------|---------------|-------|--------|-------------------|
| **odds_pipeline.py** | Fetch, normalize, validate betting odds from external sources | OddsAPI/Betfair API key, team names | Odds CSV/JSON, implied probs | data_processing.py, features.py |
| **validation.py** | Prevent time-series leakage, verify feature engineering dates, stationarity checks | Features DataFrame, match dates | Leakage report, feature cutoff enforcement | pipeline.py, train_validate |
| **model_registry.py** | Manage multiple model candidates (baseline, CatBoost, LightGBM, ensemble) | Training data, hyperparameters | Model objects, comparison metrics | pipeline.py, model_engine.py |
| **calibration.py** | Verify Poisson distribution fitting, compare predicted vs. realized scorelines | Poisson predictions, realized results, odds | Calibration metrics, adjustment suggestions | pipeline.py, stats_engine.py |
| **coordinator.py** | Distribute fixture predictions across worker tasks, manage task queue | Fixtures list, trained model | Predictions per fixture, aggregated results | model_engine.py, output.py |

---

## Data Flow Changes

### v1.0 (Current)
```
Match data → Single feature set → Single model → Single prediction → Output
```

### v2.0 (Proposed)
```
Match data + Odds data
    |
    +→ Features (Elo, trailing, Poisson) [WITH leakage checks]
    |
    +→ Multiple models (Baseline, CatBoost, LightGBM)
    |   ├→ Model 1 predicts
    |   ├→ Model 2 predicts
    |   ├→ Model 3 predicts
    |   └→ [Via Coordinator-Worker: parallel execution]
    |
    +→ Ensemble blend (weighted average)
    |
    +→ Calibration verifier (Poisson check)
    |
    +→ Output (prediction + calibration metadata)
```

**Key changes:**
1. **Odds data flow**: Enters at data layer, used for features AND baseline
2. **Leakage prevention**: Validation checks at feature building time
3. **Parallel models**: Coordinator spawns workers for each model candidate
4. **Calibration feedback**: Poisson results inform next-iteration parameter tuning

---

## Integration Points by Feature

### 1. Betting Odds Integration

**Where it fits:** Data source layer + feature layer

**Architecture:**
```python
# Phase 1: Add data source
odds_pipeline.py (NEW)
  └─ OddsAPI → normalized implied probabilities

# Phase 2: Add features
features.py (EXTENDED)
  └─ compute_odds_features(matches_df, odds_df)
       └─ Betting market implied Home/Draw/Away probabilities
       └─ Odds-model discrepancy (feature for ML)

# Phase 3: Add baseline
model_engine.py (EXTENDED)
  └─ BetMarketBaseline: predict using odds directly
```

**Integration point:** `build_features()` calls `compute_odds_features()` to add odds-derived columns

**Risk:** Odds API rate limits and data freshness; mitigation is caching + CSV fallback

---

### 2. Time-Series Leakage Prevention

**Where it fits:** Validation layer between data loading and feature building

**Architecture:**
```python
# Add validation checkpoint
validation.py (NEW)
  ├─ check_data_leakage(df)
  │   └─ For each row:
  │       ├─ Verify feature cutoff ≤ match date
  │       ├─ Check trailing stats only use past matches
  │       └─ Confirm Elo has not "seen" this match result
  │
  ├─ temporal_split_cv(df, n_splits)
  │   └─ Enhanced TimeSeriesSplit with leakage checks
  │       └─ Ensures validation set is strictly after training set
  │
  └─ stationarity_check(elo_series, form_series)
       └─ Augmented Dickey-Fuller test for non-stationarity

# Integrate into pipeline
pipeline.py (MODIFIED)
  ├─ load_data() → existing
  ├─ validate_no_leakage(df) → NEW checkpoint
  ├─ build_features(df) → existing (but now validated)
  └─ train_validate() → uses temporal_split_cv()
```

**Integration point:** `pipeline.run_pipeline()` calls `validate_no_leakage()` before `build_features()`

**Risk:** Current code doesn't explicitly check; this is a behavior change, not new code

---

### 3. Poisson Calibration Verifier

**Where it fits:** Standalone validator module, post-training

**Architecture:**
```python
# Add calibration verifier
calibration.py (NEW)
  ├─ calibration_metrics(predicted_probs, realized_outcomes)
  │   └─ Expected Calibration Error (ECE)
  │   └─ Maximum Calibration Error (MCE)
  │   └─ Brier Score
  │
  ├─ compare_poisson_vs_realized(poisson_probs, actual_results)
  │   └─ "Did Poisson distribution match real goal frequencies?"
  │
  ├─ compare_vs_odds(poisson_probs, odds_implied_probs)
  │   └─ "How close are our Poisson probs to the market?"
  │
  └─ suggest_adjustments(calibration_report)
       └─ "Try adjusting HOME_BOOST to 1.25" or "Draw adj too aggressive"

# Integrate into pipeline
pipeline.py (MODIFIED)
  ├─ train_validate() → existing
  ├─ predict_fixtures() → existing
  ├─ verify_poisson_calibration(results) → NEW checkpoint
  └─ write_outputs(calibration_report) → includes calibration data
```

**Integration point:** Called after prediction to verify model assumptions

**Risk:** Low—doesn't modify existing prediction logic, only validates it

---

### 4. Baseline Model Comparisons

**Where it fits:** Model layer, parallel with main pipeline

**Architecture:**
```python
# Add model registry
model_registry.py (NEW)
  ├─ BetMarketBaseline: predict from odds only
  ├─ SimpleLogistic: logistic regression on Elo + form
  ├─ NaiveBayes: probabilistic classifier (baseline)
  └─ EnsembleModel: weighted blend of all above

# Modify model training
model_engine.py (EXTENDED)
  ├─ create_baseline_models() → instantiate all baseline models
  ├─ train_baseline_models(X, y) → fit on same training data as main
  ├─ compare_models_cv() → evaluate all on same CV splits
  └─ select_best_model() → choose winner or ensemble

# Integrate into pipeline
pipeline.py (MODIFIED)
  ├─ train_validate() → existing CatBoost training
  ├─ train_baseline_models() → NEW: parallel baseline training
  ├─ compare_model_performance() → NEW: side-by-side metrics
  └─ write_outputs(comparison_report) → save comparison
```

**Integration point:** `train_validate()` calls `train_baseline_models()` in parallel (via threads)

**Risk:** Adding baseline models doesn't break existing predictions; worst case they're not used

---

### 5. Coordinator-Worker Pattern

**Where it fits:** Prediction orchestration layer, for parallel fixture processing

**Architecture:**
```python
# Add coordinator
coordinator.py (NEW)
  ├─ Coordinator task queue
  │   ├─ coordinate_prediction_batch(fixtures_list, model)
  │   │   └─ Split fixtures into N tasks (1 task = predict 1 fixture)
  │   │   └─ Dispatch to worker pool
  │   │   └─ Collect results, aggregate probabilities
  │   │
  │   └─ retry_logic(failed_tasks)
  │       └─ Re-dispatch failed fixtures with exponential backoff
  │
  └─ Worker process
      └─ worker_predict_fixture(fixture, model, elo_ratings)
          └─ Call model_engine.predict_gameweek()
          └─ Return prediction

# Modify prediction flow
model_engine.py (EXTENDED)
  └─ predict_gameweek() → now called by worker task (v1.0: called by pipeline)

pipeline.py (MODIFIED)
  ├─ train_validate() → existing
  ├─ predict_fixtures() → MODIFIED
  │   ├─ Sequential (v1.0)
  │   └─ Via Coordinator-Worker (v2.0)
  └─ [Pipeline logic unchanged; only execution model changes]
```

**Integration point:** `predict_fixtures()` uses `coordinator.coordinate_prediction_batch()` instead of direct loop

**Risk:** Low—coordinator is transparent wrapper; if coordinator fails, can fall back to sequential

---

## Integration Checklist

| Feature | Component | Integration Point | Breaking Change? | Fallback |
|---------|-----------|-------------------|-----------------|----------|
| Betting odds | odds_pipeline.py | build_features() | No | Skip odds features if API unavailable |
| Leakage prevention | validation.py | pipeline.run_pipeline() | No | Disable checks, warn user |
| Poisson calibration | calibration.py | write_outputs() | No | Omit calibration report |
| Baseline models | model_registry.py | train_validate() | No | Use only CatBoost |
| Coordinator-Worker | coordinator.py | predict_fixtures() | No | Fall back to sequential prediction |

**All new components are additive; none require existing code to be rewritten.**

---

## Patterns to Follow

### Pattern 1: External Data Source Integration
```python
# data/odds_source.py (analogous to existing sofascore loading)
def load_odds(filepath_or_api):
    """Load odds from file or API, normalize format."""
    odds_raw = fetch_or_read(filepath_or_api)
    odds_normalized = normalize_teams(odds_raw, glossary)
    return odds_normalized

# features.py
def compute_odds_features(matches_df, odds_df):
    """Add odds-derived columns to feature set."""
    merged = matches_df.merge(odds_df, on=['Date', 'Home', 'Away'])
    merged['Odds_Implied_Home'] = 1 / merged['HomeOdds']
    merged['Odds_Implied_Draw'] = 1 / merged['DrawOdds']
    merged['Odds_Implied_Away'] = 1 / merged['AwayOdds']
    return merged
```

**Analogy:** This mirrors existing `load_sofascore_data()` → `sofascore features in predict_gameweek()`

---

### Pattern 2: Validation Checkpoint
```python
# validation.py
def check_data_leakage(df):
    """Verify no future data leaks into features."""
    for col in ['Home_Form', 'Home_Elo', 'Poisson_Home_Win']:
        # Check: this column's data came from matches strictly before this match
        if leaked(df, col):
            raise ValueError(f"Leakage detected in {col}")

# pipeline.py
matches = load_data()
validate_no_leakage(matches)  # Add checkpoint
matches = build_features(matches)  # Proceed with validated data
```

**Analogy:** Like existing column validation in `data_processing.py`

---

### Pattern 3: Model Factory with Registry
```python
# model_registry.py
class ModelRegistry:
    def __init__(self):
        self.models = {
            'catboost': create_model('catboost'),
            'lightgbm': create_model('lightgbm'),
            'odds_baseline': BetMarketBaseline(),
            'logistic': LogisticRegression(),
        }
    
    def train_all(self, X, y):
        results = {}
        for name, model in self.models.items():
            model.fit(X, y)
            results[name] = evaluate_cv(model, X, y)
        return results

# pipeline.py
registry = ModelRegistry()
results = registry.train_all(X, y)  # Get all model results
best_model = registry.select_best(results)  # Choose winner
```

**Analogy:** Like existing `create_model()` in `model_engine.py`, but generalized

---

### Pattern 4: Coordinator-Worker Task Queue
```python
# coordinator.py
class PredictionCoordinator:
    def __init__(self, n_workers=4):
        self.pool = ThreadPoolExecutor(max_workers=n_workers)
    
    def coordinate_batch(self, fixtures, model, elo_ratings):
        tasks = []
        for fixture in fixtures:
            task = self.pool.submit(
                worker_predict_fixture,
                fixture, model, elo_ratings
            )
            tasks.append(task)
        
        results = [t.result() for t in tasks]
        return pd.concat(results)

def worker_predict_fixture(fixture, model, elo_ratings):
    """Single worker task: predict one fixture."""
    prediction = model_engine.predict_gameweek(
        fixture, elo_ratings, model, ...
    )
    return prediction

# pipeline.py
coordinator = PredictionCoordinator(n_workers=4)
predictions = coordinator.coordinate_batch(
    fixtures, best_model, elo_ratings
)
```

**Analogy:** Like existing fixture prediction loop, but parallelized via thread pool

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adding Odds as Model Feature (WRONG)
```python
# DON'T do this:
features.append('HomeOdds')  # Odds contain ground truth
model.fit(X, y)  # Model will overfit to odds
```

**Why bad:** Odds already encode market's belief; using them as features causes circular reasoning  
**Instead:** Use odds for baseline comparison or calibration, not as input feature

---

### Anti-Pattern 2: Feature Leakage in Trailing Stats (WRONG)
```python
# DON'T do this:
for idx, row in matches.iterrows():
    # Including matches AFTER this match in "trailing"
    team_history = matches[matches['Team'] == row['Team']]  # Should be .loc[:idx]
```

**Why bad:** Future matches leak into training features; model learns from outcomes it should predict  
**Instead:** Use `.loc[:idx]` to ensure only past data in trailing window

---

### Anti-Pattern 3: Coordinator-Worker Excessive Granularity (WRONG)
```python
# DON'T do this:
for feature in ['Elo', 'Form', 'Poisson']:
    # Spawn worker to compute each feature
    task = coordinator.submit(compute_feature, feature)
```

**Why bad:** Feature computation is fast; worker overhead > computation time; too many tasks  
**Instead:** Compute all features in single batch in main process; parallelize only expensive predictions

---

## Scalability Considerations

| Concern | At 100 Matches/Week | At 1,000 Matches/Week | At 10,000+ Matches/Day |
|---------|---------------------|----------------------|------------------------|
| **Data Loading** | File-based CSV sufficient | Consider DuckDB for speed | Use database (PostgreSQL) |
| **Feature Engineering** | pandas sufficient | Consider Polars for speed | Use Spark or DuckDB |
| **Model Training** | Single machine OK | Single machine OK | Distributed training (Ray, Spark) |
| **Prediction** | Sequential loop fine | Coordinator-Worker pool (4 workers) | Coordinator-Worker pool (16+ workers) |
| **Odds Fetching** | Hourly caching sufficient | Real-time API with queuing | Distributed odds cache (Redis) |

**Current v1.0:** Handles ~50 fixtures/week easily  
**v2.0 with Coordinator-Worker:** Can scale to ~500-1000 fixtures/week  
**Beyond v2.0:** Consider distributed architecture (Spark, Ray)

---

## Summary: Integration Strategy

1. **Betting odds**: Add as data source (no pipeline changes needed)
2. **Leakage prevention**: Add validation checkpoint (non-breaking)
3. **Poisson calibration**: Add verifier module (non-breaking)
4. **Baseline models**: Add to model registry (existing models still available)
5. **Coordinator-Worker**: Wrap prediction loop (transparent to callers)

**Result:** v2.0 is a superset of v1.0; existing code continues to work unchanged.
