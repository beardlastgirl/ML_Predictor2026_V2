# Feature Landscape — v2.0

**Domain:** Football match prediction with ML + Poisson + Betting Odds Integration  
**Researched:** 2026-03-22

---

## Table Stakes

Features users expect in a v2.0 prediction system. Missing = system feels incomplete.

| Feature | Why Expected | Complexity | Implementation |
|---------|--------------|------------|-----------------|
| **Betting odds baseline comparison** | "How does ML compare to bookmakers?" — Fundamental validation | Medium | Phase 1: OddsAPI integration + implied probability calculation |
| **Time-series data integrity** | "No look-ahead bias in evaluation" — Non-negotiable for credibility | Medium | Phase 2: TimeSeriesSplit + reference dates + ADF tests |
| **Poisson calibration to reality** | "Scoreline distributions should match observed history" — Core statistical requirement | Medium | Phase 3: scikit-optimize + odds-implied probabilities |
| **Baseline model accuracy** | "Bookmaker predictions achieve ~42% accuracy; we need to beat it" — Performance threshold | Low | Phase 1: Implicit (odds baseline = ~42%) |
| **Model ablation studies** | "Which features matter?" — Interpretability for improvements | Low | Existing (feature importance plots from CatBoost) |

---

## Differentiators

Features that set product apart. Not expected, but valued. Addressed by v2.0 roadmap.

| Feature | Value Proposition | Complexity | Timeline |
|---------|-------------------|------------|----------|
| **Parallel data scraping** | Reduce weekly pipeline runtime from 15min → 5min | Medium | Phase 4: TaskWeaver parallelization |
| **Agent-based orchestration** | Enable easy extension (add new data source without changing pipeline logic) | High | Phase 4: Coordinator-Worker pattern |
| **Historical odds comparison** | "Which bookmaker was sharpest?" — Market efficiency analysis | Medium | Phase 1+ (if OddsAPI historical tier unlocked) |
| **Confidence intervals on predictions** | "How uncertain is this prediction?" — Better decision-making | Medium | Phase 3: Poisson std dev + model uncertainty |
| **Automated edge detection** | "Where does ML outperform bookmakers?" — Identify profitable predictions | Medium | Phase 1-3: Implied vs predicted probability diff |

---

## Anti-Features

Features to explicitly NOT build in v2.0. Why? Scope, complexity, or diminishing returns.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time betting integration** | Requires API keys, transaction risk, legal complexity | Focus on batch predictions (weekly) |
| **Multi-league expansion** | Liga Profesional Argentina only; teams/venues differ by league | Modularize for future but focus on depth, not breadth |
| **Deep learning models (LSTM)** | Tabular data still favors tree-based; too slow to train weekly | Maintain CatBoost/LightGBM + Poisson |
| **Mobile app** | No users yet; web dashboard deferred to v3.0 | Command-line + CSV outputs (current) |
| **Live score updates during match** | Prediction is pre-match only; in-play would require different architecture | Pre-match predictions only |

---

## Feature Dependencies

```
Phase 1: Betting Odds Integration
    ├── OddsAPI data fetch
    ├── Implied probability calculator
    ├── Odds-based baseline model
    └── Feature: "Closing Odds Prob" added to predictor

Phase 2: Time-Series Leakage Prevention (depends on Phase 1)
    ├── Reference date column
    ├── TimeSeriesSplit + ADF validation
    └── CV metrics recalibrated (expect 2-3% drop)

Phase 3: Poisson Calibration (depends on Phases 1 + 2)
    ├── scikit-optimize + search space
    ├── Odds-implied probs as target
    ├── Tuned POISSON_DRAW_ADJUSTMENT
    └── Updated config.py

Phase 4: Agent Architecture (depends on Phases 1-3)
    ├── Scraping tasks parallelized
    ├── Feature engineering tasks
    ├── Prediction task
    └── TaskWeaver Coordinator orchestrates all
```

---

## MVP Recommendation

**Phase 1 MVP (Week 1-2):**
1. ✅ OddsAPI integration (closing odds → implied probabilities)
2. ✅ Odds-based baseline model (accuracy: ~42%)
3. ✅ ML model comparison (accuracy: target 44-46%)

**Defer to Phase 2:**
- Leakage checks (necessary but not MVP-blocking)

**Defer to Phase 3-4:**
- Poisson tuning (calibration nice-to-have if Phase 1 shows positive variance)
- Agent architecture (infrastructure, not prediction logic)

---

## Feature Details by Phase

### Phase 1: Betting Odds Integration

**What Gets Built:**
```python
# src/odds_engine.py
class OddsProvider:
    def __init__(self, api_key):
        # Cache management, API rate limiting
    
    def get_odds(self, league="AR", date=today):
        # Fetch from OddsAPI
        # Return: {match_id: {home_prob, draw_prob, away_prob}}
    
    def get_baseline_predictions(self, fixtures):
        # Convert implied probs to 1X2 predictions
        # Return: accuracy metrics vs actual results
```

**Integration:**
- In `src/model_engine.py:predict_gameweek()`:
  ```python
  # Add odds features
  fixtures_df['Odds_Home_Prob'] = fixtures_df.apply(lambda x: odds_provider.get_odds(x['match_id'])['home'], axis=1)
  fixtures_df['Odds_Draw_Prob'] = ...
  fixtures_df['Odds_Away_Prob'] = ...
  
  # Create baseline model
  baseline_accuracy = (odds_predictions == actual).mean()
  ```

**Success Metrics:**
- Baseline accuracy: ≥ 42% (bookmaker level)
- API response time: < 500ms per match
- Cache hit rate: > 90% (reuse previous weeks)

---

### Phase 2: Time-Series Leakage Prevention

**What Gets Built:**
```python
# src/validation.py
def check_time_series_leakage(X, y, reference_dates, alpha=0.05):
    """
    Detect look-ahead bias in features.
    
    For each TimeSeriesSplit fold:
      1. Train ADF test on training features
      2. If p-value < alpha: flag potential leakage
      3. Return leakage report
    """
    # Run ADF tests, log warnings
    # Suggest feature engineering improvements
```

**Integration:**
- In `src/pipeline.py:train_validate()`:
  ```python
  # Replace random CV with TimeSeriesSplit
  cv = TimeSeriesSplit(n_splits=5)
  
  # Add leakage checks
  leakage_report = check_time_series_leakage(X_train, y_train, reference_dates)
  
  # Recalculate metrics
  cv_accuracies = [...]  # Expect 2-3% drop from Phase 1
  ```

**Success Metrics:**
- No ADF test flags (p-value > 0.05) in any fold
- CV metrics drop 2-3% (realistic noise)
- Predictions on holdout 2026 season match ground truth

---

### Phase 3: Poisson Calibration

**What Gets Built:**
```python
# scripts/calibrate_poisson.py (one-time execution)
from skopt import gp_minimize

def objective(params):
    """Minimize log-loss: predicted Poisson probs vs odds-implied probs."""
    poisson_probs = calculate_outcome_probabilities(
        params['poisson_draw_adj'],
        params['home_boost']
    )
    odds_probs = load_odds_implied_probabilities()
    
    # Log-loss: -mean(log(predicted_prob[actual_outcome]))
    return log_loss(odds_probs, poisson_probs)

# Search space
space = {
    'poisson_draw_adj': (0.75, 0.95),
    'home_boost': (1.15, 1.30)
}

# Run 100 iterations of Bayesian optimization
result = gp_minimize(objective, space, n_calls=100)

# Save optimal params
optimal_params = result.x
print(f"Optimal POISSON_DRAW_ADJUSTMENT: {optimal_params[0]}")
print(f"Optimal HOME_BOOST: {optimal_params[1]}")
# Update src/config.py
```

**Integration:**
- One-time script: `python scripts/calibrate_poisson.py`
- Updates `src/config.py`:
  ```python
  POISSON_DRAW_ADJUSTMENT = 0.87  # Was 0.85
  HOME_BOOST = 1.24               # Was 1.22
  ```

**Success Metrics:**
- Poisson log-loss ≤ baseline (no regression)
- Predicted scoreline distribution matches observed (chi-square test p > 0.05)
- Blended model (60% ML + 40% Poisson) achieves > 44% accuracy

---

### Phase 4: Agent Orchestration

**What Gets Built:**
```
src/
├── coordinator.py           # TaskWeaver Coordinator
├── tasks/
│   ├── scrape_fbref.py      # Worker: FBref stats
│   ├── scrape_sofascore.py  # Worker: Sofascore standings
│   ├── scrape_tyc.py        # Worker: TyC fixtures
│   ├── build_features.py    # Worker: Feature engineering
│   └── predict_gameweek.py  # Worker: Model predictions
└── run_coordinator.py       # Main orchestration
```

**Integration:**
- In `main.py`:
  ```python
  from src.coordinator import run_pipeline_with_agents
  
  result = run_pipeline_with_agents()
  # Replaces current sequential pipeline
  ```

**Architecture:**
```
Coordinator (Main):
  ├── [Parallel] Task: Scrape FBref (depends on schedule)
  ├── [Parallel] Task: Scrape Sofascore (depends on schedule)
  ├── [Parallel] Task: Scrape TyC (depends on schedule)
  ├── [Sequential] Task: Build Features (depends on scraping tasks)
  ├── [Sequential] Task: Train Model (depends on features)
  └── [Sequential] Task: Predict Gameweek (depends on model + new matches)
```

**Success Metrics:**
- End-to-end pipeline runtime: 15min → 5min (3x faster)
- All tasks complete without race conditions
- Easy to add new task: no pipeline.py changes required

---

## Prioritization Matrix

| Feature | Value | Effort | Priority |
|---------|-------|--------|----------|
| Phase 1: Odds Integration | High (baseline comparison) | Medium (2 libs, 1 API) | **P0** |
| Phase 2: Leakage Prevention | High (core validity) | Medium (validation logic) | **P0** |
| Phase 3: Poisson Calibration | Medium (optimization, not required for v2.0 MVP) | Medium (tuning script) | **P1** |
| Phase 4: Agent Architecture | Medium (infra, not prediction logic) | High (refactoring) | **P2** |

---

## Success Criteria

### Phase 1
- ✅ OddsAPI integration complete
- ✅ Baseline model accuracy ≥ 42%
- ✅ ML model accuracy > baseline (target: 44-46%)
- ✅ Feature added: Odds_Home_Prob, Odds_Draw_Prob, Odds_Away_Prob

### Phase 2
- ✅ TimeSeriesSplit replaces random CV
- ✅ ADF tests pass (no leakage detected)
- ✅ CV metrics recalibrated; realistic 2-3% drop acceptable
- ✅ Holdout validation on 2026 season data

### Phase 3
- ✅ Poisson parameters optimized via scikit-optimize
- ✅ Poisson log-loss ≤ baseline
- ✅ Scoreline distribution matches observed history

### Phase 4
- ✅ Pipeline runtime reduced 3x (15min → 5min)
- ✅ Scraping parallelized without race conditions
- ✅ New data source can be added without modifying pipeline.py

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| OddsAPI 500 req/month limit exhausted | Can't fetch odds → baseline breaks | Cache locally; pre-fetch weekly not daily; fallback to CSV |
| Poisson calibration over-fits to Liga Profesional | Model doesn't generalize to other leagues | Use rolling window; validate on holdout season |
| Agent refactoring introduces race conditions | Pipeline becomes unreliable | Phase 4 is P2; get phases 1-3 rock solid first |
| Time-series validation too strict | Flags legitimate features as leakage | Use 95% significance level (not 99%) |

---

## Sources

- **OddsAPI**: https://the-odds-api.com/ (REST API docs)
- **odds-converter**: https://github.com/s0i/odds-converter (Python library for odds math)
- **scikit-optimize**: https://scikit-optimize.github.io/ (Bayesian optimization)
- **TaskWeaver**: https://github.com/microsoft/TaskWeaver (Agent coordination framework)
- **Time-Series CV**: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html (scikit-learn docs)

---

**Confidence:** HIGH  
All features scoped to achievable MVPs. Dependencies clear. Risks documented and mitigable.

Prioritize:
1. **Calibrated 1X2 Probabilities**: Using Elo + Form as features.
2. **Dixon-Coles Scoreline Engine**: For realistic probability spreads.
3. **Closing Odds Integration**: To benchmark model accuracy vs. market consensus.

Defer: **xT / Kinematic Features**: High data cost for marginal gains in early development phases.

## Sources

- [Pinnacle: The Importance of Closing Line Value](https://www.pinnacle.com/en/betting-resources/)
- [Soccermatics (David Sumpter): xG and Advanced Metrics](https://soccermatics.org/)
- [EconPapers: The Bivariate Poisson Distribution in Football Modeling](https://econpapers.repec.org/)
