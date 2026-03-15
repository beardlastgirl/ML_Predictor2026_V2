# ML_Predictor2026_V2 - Enhanced Prediction System

## What This Is

A robust, agent-based football prediction system for Argentine football leagues (Liga Profesional Argentina). It combines Poisson distribution for goal modeling with machine learning (LightGBM/CatBoost) to predict match outcomes and scorelines. The system is being rebuilt to deliver genuinely skillful predictions with realistic scoreline distributions, clean feature engineering, and modular agent architecture.

## Core Value

Deliver match outcome (1X2) and scoreline predictions that clearly beat naive baselines (e.g., "always 1-1") with realistic probability distributions, not concentrated around generic scores.

## Requirements

### Validated

- ✓ Existing Poisson + ML prediction engine — existing codebase
- ✓ Modular src/ architecture (config, features, model_engine, stats_engine) — existing
- ✓ Multiple data scrapers (FBref, FootyStats, TyC, Sofascore) — existing

### Active

- [ ] **DATA-01**: Integrate betting odds datasets as features and calibration baseline
- [ ] **DATA-02**: Fix data alignment issues (features correctly aligned with match dates)
- [ ] **DATA-03**: Improve data quality pipeline (handle missing values, inconsistencies)
- [ ] **POISS-01**: Fix Poisson calibration to produce realistic scoreline spread (not clustered 1-1, 2-1)
- [ ] **POISS-02**: Revisit per-team attack/defense strength calculation
- [ ] **POISS-03**: Properly derive match outcome probabilities from goal distributions
- [ ] **MODEL-01**: Implement proper baselines (naive: always 1-1, historical frequencies)
- [ ] **MODEL-02**: Add proper scoring rules (log loss, Brier score, ranked probability score)
- [ ] **MODEL-03**: Fix train/validation/test time separation to prevent leakage
- [ ] **MODEL-04**: Improve feature set (form, xG, congestion, home/away strength)
- [ ] **AGENT-01**: Modular agent architecture: data scraper → feature engineer → trainer → inference
- [ ] **AGENT-02**: Pluggable design for swapping models and data sources
- [ ] **AGENT-03**: Autonomous query/train/predict agent capabilities

### Out of Scope

- Real-time betting integration — focus on batch prediction, not live betting
- Multi-league expansion — stay focused on Argentine leagues for now
- Deep learning models (LSTM, transformers) — keep to tree-based + Poisson for now
- Scraping odds from betting sites — use existing odds datasets instead

## Context

**Current state:**
- Model accuracy: ~42% (time-series CV), log-loss: 1.090
- Predictions cluster around 1-1 and 2-1 regardless of match context
- 21 features including 10 Poisson-derived features
- 6049 matches in training data
- Multiple scrapers working but potential quality/alignment issues

**Technical environment:**
- Python 3.8+ in .venv at project root
- CatBoost (default) / LightGBM support
- Selenium, Playwright, CDP for scraping
- Git repository at project root

**Known issues to address:**
- Poisson calibration producing narrow scoreline distributions
- Unclear if features have leakage or alignment issues
- No proper baseline comparison implemented
- Evaluation metrics limited (accuracy only, no proper scoring rules)

## Constraints

- **Data**: Betting odds via datasets (not scraping) — practical, avoids blocking
- **Timeline**: Iterative improvement — fix core before expanding
- **Tech stack**: Python ecosystem, keep existing modular architecture
- **Scope**: Argentine leagues only (Liga Profesional) — focus depth over breadth
- **Evaluation**: Must beat naive baseline with practical (not just statistical) improvement

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix Poisson before outcome ML | Scoreline calibration is root cause of generic predictions | — Pending |
| Use odds datasets not scrapers | Faster, avoids anti-bot battles, focus on modeling not infra | — Pending |
| Agent architecture alongside fixes | Modular design enables experimentation without rewrites | — Pending |
| Beat naive baseline first | Clear, achievable target before tackling bookmaker lines | — Pending |
| Practical improvement over statistical significance | Need observable improvement first, rigor after | — Pending |

---
*Last updated: 2026-03-15 after project initialization*
