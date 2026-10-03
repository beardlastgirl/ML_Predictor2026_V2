# Domain Pitfalls: ML Prediction System v2.0 Features

**Project:** ML_Predictor2026_V2  
**Researched:** 2026-03-21  
**Focus:** Adding odds integration, leakage prevention, Poisson calibration, baseline comparisons, and agent architecture  
**Scope:** Pitfalls specific to ADDING these capabilities to an existing prediction system

---

## Critical Pitfalls (Cause Rewrites/Data Corruption)

### Pitfall 1: Forward-Looking Bias in Odds Integration
**What goes wrong:** Betting odds are incorporated as features BEFORE the match, but the model learns to predict the DIRECTION of odds movement, not actual outcomes. Model becomes useless out-of-sample because odds you scrape today are AFTER-the-fact and market-efficient.

**Why it happens:**
- Odds are scraped post-match or with timestamp confusion (unclear if pre-match or post-match)
- No separation between "opening odds" (true pre-match) vs "closing odds" (post-match, contains information)
- Timing metadata lost during data pipeline
- Model assumes odds are exogenous but they're actually outcomes of information discovery

**Warning signs:**
- Model performance drops suddenly when moving from backtest to live predictions
- Feature importance shows odds as TOP predictive feature (market already knows this)
- Prediction probabilities nearly identical to odds-implied probabilities (model copied the odds)
- High training accuracy but poor validation cross-validation performance

**Consequences:**
- Model learns to "predict" odds direction, not match outcomes
- Live predictions collapse because odds are already settled
- Data scientists waste weeks tuning a worthless model
- False confidence from backtesting

**Prevention:**
- **MANDATORY timestamp protocol:** Record scrape_time, match_time, odds_timestamp separately
- Store odds with SOURCE METADATA: "opening odds at T-3 days" vs "live odds at T-0 days"
- Validate: Historical odds must be strictly BEFORE match kickoff (add check)
- Never merge odds by match ID alone—require temporal constraint
- For backtesting: Use ONLY opening odds, never live/closing odds
- Add explicit feature: "days_until_kickoff" to detect odds-recency effects
- Test: Retrain model excluding odds features—should still have meaningful performance

**Detection:**
```python
# Check: Are odds features correlated with model prediction?
# If odds correlation > 0.95, odds are likely post-match or market-absorbed
# Check: Does removing odds hurt validation CV performance significantly?
# If not, odds are redundant (market already priced information)
```

**Testing strategy:**
- Unit test: Verify all odds have timestamp < match kickoff
- Integration test: Train model on subset with odds, subset without—compare CV accuracy
- Walk-forward test: Predict next 10 matches using only "pre-match" odds, measure error

---

### Pitfall 2: Train/Test Leakage in Trailing Statistics
**What goes wrong:** When computing trailing averages (last 8 matches), the pipeline accidentally includes the CURRENT MATCH in both training AND test sets. Team's stats for match N include match N itself, violating causality.

**Why it happens:**
- Trailing features computed ONCE on all historical data, then reused
- Timeline confusion: Code sorts by date, but feature calculation loops through chronologically WITHOUT resetting after each match
- Sofascore data scraped AFTER matches (contains results), merged with pre-match features
- Multiple data sources with different update frequencies mixed without temporal separation

**Warning signs:**
- Training accuracy unrealistically high (>50% on 3-class problem seems too good)
- Log-loss significantly lower in training than validation CV
- Model performance drops sharply when predicting next round (accumulation of errors)
- Feature importance shows trailing averages as TOP predictive features
- Year-over-year model performance degradation (leakage compounds over time)

**Consequences:**
- Model learns from "tomorrow's" stats to predict "today's" match
- Backtesting overoptimistic, live predictions fail
- Overfitting is undetectable because leakage IS real information
- When new matches arrive, stats suddenly become outdated (leakage assumption breaks)

**Prevention:**
- **STRICT chronological barriers:** For each match, compute trailing stats BEFORE that match date only
- Refactor `compute_trailing_features()` to use POINT-IN-TIME approach:
  ```python
  # WRONG:
  for match in all_matches:
      stats = get_trailing_stats(history[-8:])  # history grows as you loop
  
  # RIGHT:
  for idx, match in enumerate(all_matches):
      history_before_match = [m for m in all_matches[:idx] if m.date < match.date]
      stats = get_trailing_stats(history_before_match[-8:])
  ```
- Timestamp all feature computations: Feature value is snapshot AS OF match date
- Never merge Sofascore data by team name alone—require DATE constraint
- Add explicit validation: For each feature row, verify all contributing data points are BEFORE match date
- During training, time-series split MUST respect temporal causality
  - sklearn's TimeSeriesSplit already does this, but verify its being called correctly
  - Check: No test fold match date < training fold match date

**Detection:**
```python
# Check: Do trailing averages include current match?
# Verify: For match on 2026-03-21, does trailing average include only matches BEFORE 2026-03-21?
# Verify: historical_matches.csv has DATE < fixture.date for all features
```

**Testing strategy:**
- Unit test: For each match, verify trailing stats only use matches < match_date
- Temporal sanity check: Pick 3 random matches, manually compute trailing stats, verify against code
- Leakage detector: Remove trailing stats features, check if model still has same accuracy (should drop if leakage was real)
- Walk-forward: Train on first 100 matches, predict match 101, verify only 100 matches were used

---

### Pitfall 3: Poisson Calibration Overfitting to Historical Odds
**What goes wrong:** When calibrating Poisson parameters (HOME_BOOST, POISSON_DRAW_ADJUSTMENT) using Shin method or empirical outcome frequencies, the model fits the ODDS (which reflect market consensus) instead of ACTUAL goal-scoring process. Result: Poisson predictions match odds perfectly but fail to identify mispricings.

**Why it happens:**
- Odds available in historical data, so they're used as "ground truth" for calibration
- Shin method (extracting implied probabilities from odds) used to calibrate Poisson
- POISSON_DRAW_ADJUSTMENT tuned to match league draw frequency (which is already reflected in odds)
- Circular dependency: Poisson → calibrate to odds → use odds in features → model learns odds patterns

**Warning signs:**
- Poisson probabilities and odds-implied probabilities nearly identical
- Model trained with Poisson + odds as features has zero improvement over odds alone
- Poisson calibration parameters different across seasons/divisions (suggests overfitting)
- When odds unavailable (live scenarios), predictions revert to worse performance
- Backtesting shows edge over odds, but live (where odds are contemporaneous) shows no edge

**Consequences:**
- Model becomes odds-follower, not odds-predictor
- Loses ability to identify mismatches (which are where value exists)
- Poisson becomes redundant feature (model just copies odds)
- In production (where odds are live, not historical), performance collapses

**Prevention:**
- **Never calibrate Poisson using the same odds you'll use as features**
- Split odds chronologically: Use odds from SEASON N to calibrate, odds from SEASON N+1 to validate
- Alternative: Calibrate Poisson on goal-scoring data ONLY, not odds
  - Base xG formula on shot data (xG metrics), not odds
  - Calibrate Poisson PMF parameters on goal distributions, not outcome frequencies
- Store calibration metadata: "Poisson calibrated on Season 2024, using goal data"
- Cross-validate calibration: Calibrate on odd seasons, test on even seasons
- Add feature: "Odds_vs_Poisson_Diff" = |odds_prob - poisson_prob|, measure its predictive value
  - If zero predictive value, they're overfitting to same signal

**Detection:**
```python
# Check: Is Poisson calibration source documented?
# Check: Does removing Poisson features improve model? (should not, if calibrated correctly)
# Check: Correlation between Poisson features and odds features > 0.90? = overfitting
```

**Testing strategy:**
- Cross-season validation: Calibrate on 2024, test on 2025 (should degrade gracefully, not collapse)
- Ablation test: Remove odds from training, retrain model, does Poisson performance match previous?
- Sensitivity analysis: Change POISSON_DRAW_ADJUSTMENT by ±0.1, how much does accuracy change?
- Out-of-sample odds comparison: On recent fixtures, do Poisson and actual odds diverge? If not, overfitted

---

### Pitfall 4: Data Contamination During Coordinator-Worker Agent Communication
**What goes wrong:** In distributed agent architecture (Coordinator assigns work to Workers), agents share DataFrames or mutable objects by REFERENCE, not by VALUE. One Worker modifies data, all others see the mutation. State gets corrupted mid-training across rounds.

**Why it happens:**
- Coordinator passes `matches_df` to Worker threads without `.copy()`
- Workers compute features in-place (df.loc[], df[col] = ...) instead of returning new DataFrames
- Shared state for Elo ratings dictionary—Worker updates Elo, Coordinator sees stale values
- No serialization/deserialization boundary between processes
- Testing done single-threaded, parallelization introduces subtle race conditions

**Warning signs:**
- Random training failures that can't be reproduced
- Feature values inconsistent between runs (different from non-parallel run)
- Elo ratings jump suddenly mid-training
- One test case passes when run alone, fails when run with other tests
- Memory usage lower than expected (workers sharing memory = leakage)
- TimeSeriesSplit test folds contain future data (contamination from parallel compute)

**Consequences:**
- Model corruption: Elo ratings become invalid
- Training fails mid-run with cryptic errors
- Cross-validation folds not independent (statistics become invalid)
- Data scientists can't debug because issue is non-deterministic
- Performance in production differs from training

**Prevention:**
- **Enforce immutability at agent boundaries:**
  - Coordinator → Worker: `df.copy()` (deep copy)
  - Worker → Coordinator: return new DataFrame, don't modify input
- Use immutable data structures for shared state:
  ```python
  # WRONG:
  shared_elo = {"Team1": 1500}  # Coordinator modifies, Worker sees mutation
  
  # RIGHT:
  worker_elo = {"Team1": 1500}  # Each worker gets copy
  # Coordinator merges worker results after task complete
  ```
- Pass data via MESSAGE QUEUE or explicitly serialized format (JSON/pickle)
  - Prevents accidental sharing
  - Forces contract definition (what Worker outputs)
- Add assertion at each boundary:
  ```python
  worker_input_hash = hash(worker_input)
  worker_output = worker_task(worker_input)
  assert hash(worker_input) == worker_input_hash  # Verify input not mutated
  ```
- TimeSeriesSplit: Assign fold boundaries in Coordinator, Workers receive fold_idx+boundaries, not raw DataFrame slices
- Elo rating updates: Coordinator collects all updates, applies serially AFTER all Workers complete (no concurrent updates)

**Detection:**
```python
# Check: Are DataFrames copied at agent boundaries?
# Check: Are mutable objects (dicts, lists) shared or copied?
# Check: Run model 10x, all 10 should produce identical Elo ratings
```

**Testing strategy:**
- Unit test: Pass df to mock worker function, verify Worker can't mutate original
- Integration test: Run training with 1 worker (serial), 4 workers (parallel), both should give same results
- Stress test: Run training 100x with parallel agents, measure variance (should be zero)
- Serialization test: Coordinator → serialize data → Worker → deserialize, verify values exact match

---

## Moderate Pitfalls

### Pitfall 5: Baseline Comparison Methodology Errors
**What goes wrong:** When comparing new model to baseline, the comparison is unfair: different features, different data sources, different temporal windows, or same test set used for tuning.

**Why it happens:**
- Baseline model (e.g., Elo-only) trained on different feature set than new model
- Baseline doesn't use Sofascore data because it wasn't available when baseline was built
- Model selection tuned on test set (looking at test performance to choose hyperparameters)
- Different feature engineering for baseline vs new model (baseline uses lagged features, new uses rolling window)
- Baseline uses different cross-validation strategy (random split vs time-series split)

**Warning signs:**
- Baseline model missing obvious features (defense metrics, recent form)
- New model shows improvement only on specific match types (suggests data distribution mismatch)
- Improvement disappears when baseline gets access to same data sources
- Hyperparameters tuned using test set performance
- CV performance significantly better than hold-out test performance

**Consequences:**
- Claimed improvement is artifact of comparison bias, not real model quality
- When baseline is updated to match new model's inputs, improvement vanishes
- Stakeholders distrust results if discovered
- Resources wasted on "improvements" that don't transfer to production

**Prevention:**
- **Define baseline BEFORE building new model:**
  - Document exactly what features baseline uses
  - Freeze baseline code/hyperparameters
  - Use identical train/val/test splits for both
- **Identical data sources:** If new model uses Sofascore, baseline must too
- **Identical CV strategy:** Both models use TimeSeriesSplit with same fold boundaries
- **Separate tuning/test sets:** Hyperparameters tuned on CV performance, never test set
- Create "matched baseline" that uses same input features as new model, only different algorithm
- Document all differences explicitly:
  ```python
  baseline_config = {
      "features": ["Elo_Diff", "Form_Diff"],  # MINIMAL
      "model": "LogisticRegression",
      "cv_strategy": "TimeSeriesSplit(n_splits=5)",
  }
  new_model_config = {
      "features": ["Elo_Diff", "Form_Diff", "xG_home", "xG_away", "Sofascore_Position"],  # RICH
      "model": "CatBoost",
      "cv_strategy": "TimeSeriesSplit(n_splits=5)",  # IDENTICAL
  }
  ```
- **Ablation test:** Remove new features one-by-one, measure performance degradation
  - If new feature improves baseline → feature is valuable
  - If not → feature is correlated with existing features (redundant)

**Detection:**
```python
# Check: Do baseline and new model use same data sources?
# Check: Do baseline and new model use same CV strategy?
# Check: Were hyperparameters tuned on train/val or on test?
# Check: If baseline had access to new data sources, would it improve?
```

**Testing strategy:**
- Fair comparison test: Train both on identical data/splits, measure accuracy delta
- Ablation test: Remove new feature from new model, does accuracy match baseline?
- Hyperparameter sensitivity: Tune baseline as aggressively as new model, compare again
- Cross-validation stability: Both models should have similar CV variance

---

### Pitfall 6: Temporal Instability in Odds Integration
**What goes wrong:** Betting odds patterns are non-stationary. Model trained on 2024 odds with certain market behavior, applied to 2025 where odds market has changed. Model assumes odds-outcome relationship is stable, but it shifts seasonally or due to market evolution.

**Why it happens:**
- Odds-to-outcome relationship (implied probability vs actual frequency) changes with market liquidity
- Different bookmakers have different biases (some overvalue home teams, others undervalue draws)
- Market efficiency varies: early season odds are less efficient than mid-season
- Exchange odds vs bookmaker odds have different distributions
- No temporal grouping: model trained on mixed seasons without seasonality adjustment

**Warning signs:**
- Model accuracy degrades in specific months (e.g., April-June worse than Jan-Mar)
- Predicted probabilities shift systematically after seasonal break
- Model fails disproportionately on newly promoted teams (data for new odds distribution)
- Accuracy improving early season, degrading late season

**Consequences:**
- False confidence from historical backtesting (averaged across stable periods)
- Predictions systematically biased in specific seasons/months
- Feature importance estimates unreliable (odds contribution varies temporally)

**Prevention:**
- **Temporal stratification in cross-validation:**
  ```python
  # Instead of random TimeSeriesSplit:
  # Group by season + perform stratified time-series CV
  # Verify: Test fold contains different season than train fold
  ```
- Store odds source metadata: "bookmaker X", "timestamp T", "market efficiency E"
- Add seasonal feature: month, day-of-week (capture odds patterns that shift seasonally)
- Monitor model performance over time: track accuracy by month, alert if degradation
- Retrain model monthly or quarterly, not just once per season
- Test: Train on Season A, test on Season B—accuracy should be stable

**Testing strategy:**
- Seasonal hold-out: Train on Jan-Sep, test on Oct-Dec, measure accuracy
- Repeat for all possible seasonal splits
- Monthly accuracy tracking: Plot accuracy by month, check for trend
- Year-over-year comparison: 2024 vs 2025 odds accuracy on same matches (if available in archives)

---

### Pitfall 7: Poisson Assumption Violations in Injury/Formation Changes
**What goes wrong:** Poisson distribution assumes goal-scoring is a stationary stochastic process. When key player injured or formation changes mid-season, xG distribution shifts, but Poisson parameters (calibrated on pre-injury data) become invalid.

**Why it happens:**
- Poisson calibration uses season-wide averages, doesn't adapt to roster changes
- xG formula (HOME_BOOST, attack/defense weights) fixed for entire season
- No detection of tactical changes or significant injuries
- Model assumes historical patterns will continue

**Warning signs:**
- Predictions systematically biased after key player injury (over/under-estimates goals)
- Model performance drops after mid-season roster changes
- Specific team's predictions become less accurate after formation change
- xG estimates for affected team don't match actual goal patterns

**Consequences:**
- Predictions invalid for matches post-injury or post-formation change
- Feature values stale (based on pre-change team composition)
- Elo ratings continue assuming pre-injury strength (lag behind reality)

**Prevention:**
- **Add recalibration trigger:** If team xG differs from actual goals by >0.5 for 3 consecutive matches, flag for recalibration
- Store Poisson parameters as VERSION rather than global constant
  - "Poisson_v1": Season start calibration
  - "Poisson_v2": After injury update (if detected)
- Add injury/roster change metadata: "Injury on 2026-02-15: key striker out 4 weeks"
- Monitor team xG vs actual goals drift: if diverging, re-estimate attack/defense factors
- Use ROLLING calibration instead of season-wide: Retrain Poisson parameters every 10 matches

**Detection:**
```python
# Check: xG vs Goals residual for each team
# If |actual_goals - expected_goals| > 1.0 for 3+ matches, flag team
# Check: Are Poisson parameters documented with calibration date?
```

**Testing strategy:**
- Simulate injury: Remove key player stats from training data for team, see how predictions change
- Trigger recalibration: After detecting injury, retrain Poisson params, verify predictions improve
- Drift detection: Track xG-vs-goals error over time, verify it stays within bounds

---

## Minor Pitfalls

### Pitfall 8: Coordinator State Not Persisted Between Runs
**What goes wrong:** In agent architecture, Coordinator maintains state (Elo ratings, model, feature cache) in memory. If Coordinator restarts (crash, deployment), all state is lost and must be recomputed from scratch, taking hours.

**Why it happens:**
- State stored in Python dict/variables, not persisted to disk
- No checkpoint mechanism between prediction rounds
- Assumptions: "Coordinator always runs" (fragile)

**Prevention:**
- Serialize Coordinator state to disk (pickle/JSON) after each round
- On startup, check for latest checkpoint and resume from there
- Include timestamp in checkpoint so stale checkpoints can be detected

**Testing strategy:**
- Checkpoint/restore test: Save state, restart Coordinator, verify state restored correctly

---

### Pitfall 9: Feature Engineering Inconsistency Between Offline and Live Prediction
**What goes wrong:** Offline training uses weekly data (fixed cutoff), live predictions use current data (moving cutoff). Feature definitions differ: trailing averages computed differently, Sofascore data update frequency different.

**Why it happens:**
- Training script and live prediction script diverged
- Sofascore API updates daily, training script runs weekly (data staleness)
- No feature versioning or schema validation

**Prevention:**
- Single source of truth for feature engineering
- Validate: Features computed offline match features in live prediction
- Add feature schema: Version all feature definitions
- Unit test: Predict same fixture offline and live, features should be identical

**Testing strategy:**
- Consistency test: Compute features for upcoming match in training context and live context, verify identical

---

### Pitfall 10: Multi-Match Elo Update Race Conditions
**What goes wrong:** If Coordinator and multiple Workers both update Elo ratings for same match, final Elo value is undefined (last write wins).

**Why it happens:**
- Elo updates assumed atomic but aren't in parallel context
- No locking mechanism on shared Elo dict

**Prevention:**
- Elo updates collected by each Worker, applied serially by Coordinator AFTER all Workers complete
- Use queue/message passing for updates, not direct dict modification

**Testing strategy:**
- Parallel Elo test: Have 10 workers update same match, verify final Elo deterministic

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **DATA-01: Odds Integration** | Forward-looking bias, temporal mismatch | Implement timestamp protocol, validate pre-match timestamps, never merge by ID alone |
| **DATA-02: Leakage Prevention** | Train/test contamination in trailing stats, sofascore merge | Point-in-time feature engineering, temporal validation, unit test each date boundary |
| **POISS-01: Calibration** | Overfitting to historical odds, assumption violations | Separate calibration data from validation data, seasonal recalibration |
| **MODEL-01: Baseline Comparison** | Unfair comparison (different features, different CV) | Freeze baseline before building new model, identical data/CV strategy for both |
| **AGENT-01: Coordinator-Worker** | Data corruption via reference sharing, state loss | Deep copy at boundaries, serialize state, immutable data structures |

---

## Integration Pitfalls (Cross-Feature)

### Pitfall: Odds + Leakage Cascade
**Scenario:** Sofascore standings include current-round statistics (already-played matches). Odds scraped at different times. Together, they create multiple leakage paths.

**Prevention:**
- Sofascore merge: Strict date constraint (standings_date < match_date - 1 day)
- Odds validation: Odds timestamp < match kickoff
- Unit test combination: Merge odds + sofascore, verify no leakage

---

### Pitfall: Poisson + Baseline Comparison Bias
**Scenario:** New Poisson model trained on same data as baseline, but baseline tuned on old hyperparameters. Comparison shows improvement, but it's actually just from re-tuning hyperparameters, not from Poisson.

**Prevention:**
- Retune baseline hyperparameters when adding Poisson features
- Ablation: Remove Poisson features, retrain baseline, measure accuracy
- Fair comparison: New model = baseline + Poisson features, compare to baseline

---

### Pitfall: Agent Parallelization + Feature Cache
**Scenario:** Feature cache shared between Workers, one Worker modifies cache while another reads it. Cache becomes corrupted.

**Prevention:**
- Each Worker gets own copy of cache
- Cache read-only from Coordinator perspective

---

## Sources

- **Time-series leakage:** Kaggle "Leakage in Time-Series" competitions and post-mortems
- **Betting odds bias:** "Efficient Markets Hypothesis" (Fama 1970), modern sportsbook bias research
- **Poisson calibration:** "Calibrating Sports Models" research, comparison to Weibull/Negative Binomial alternatives
- **Concurrent data structures:** Python threading/multiprocessing documentation, race condition case studies
- **ML baselines:** "Comparing ML Models" guidelines (MLOps community standards)

---

## Testing Checklist for Each Pitfall

Before moving to next phase, verify:

- [ ] **DATA-01**: Odds have timestamps, all < match kickoff, validated in unit test
- [ ] **DATA-02**: Trailing features computed point-in-time, random walk test passes, CV folds independent
- [ ] **POISS-01**: Poisson calibration data != validation data, seasonal cross-validation stable
- [ ] **MODEL-01**: Baseline frozen, identical features/CV/data to new model, ablation test documented
- [ ] **AGENT-01**: Data copied at agent boundaries, 100 parallel runs produce identical results, state persisted

---

## Recommended Research Phases

| Feature | Research Phase | Validation | Testing Complexity |
|---------|-----------------|------------|-------------------|
| **DATA-01** | Phase 2 | Timestamp protocol | High (temporal validation) |
| **DATA-02** | Phase 2 | Point-in-time checks | Very High (leakage detection) |
| **POISS-01** | Phase 3 | Cross-season validation | High (calibration robustness) |
| **MODEL-01** | Phase 3 | Fair comparison metrics | Medium (ablation studies) |
| **AGENT-01** | Phase 4 | Stress testing | High (concurrency testing) |

