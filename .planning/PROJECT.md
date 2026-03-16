# ML_Predictor2026_V2 - Enhanced Prediction System

## What This Is

A robust, agent-based football prediction system for Argentine football leagues (Liga Profesional Argentina). It combines Poisson distribution for goal modeling with machine learning (LightGBM/CatBoost) to predict match outcomes and scorelines. The system is being rebuilt to deliver genuinely skillful predictions with realistic scoreline distributions, clean feature engineering, and modular agent architecture.

## Core Value

Deliver match outcome (1X2) and scoreline predictions that clearly beat naive baselines (e.g., \"always 1-1\") with realistic probability distributions, not concentrated around generic scores.

## Current Milestone: v2.0 Core Engine Rebuild & Calibration

**Goal:** Transform the system from a generic \"running\" state to a skillful prediction engine that beats naive baselines and provides realistic scoreline distributions.

**Target features:**
- Betting odds integration (closing odds as features and calibration baselines)
- Systematic data alignment and leakage prevention (time-series validation)
- Advanced Poisson/Score modeling (fixing the 1-1/2-1 clustering issue)
- Modular Agent Architecture (Scraper -> Feature -> Trainer -> Inference)
- Proper Scoring Rules (Log Loss, Brier Score, RPS)

## Requirements

### Validated

- ✓ Modular src/ architecture (config, features, model_engine, stats_engine) — existing
- ✓ Multiple data scrapers (FBref, FootyStats, TyC, Sofascore) — existing

### Active

- [ ] **DATA-01**: Integrate betting odds datasets as features and calibration baseline
- [ ] **DATA-02**: Fix data alignment issues (features correctly aligned with match dates)
- [ ] **DATA-03**: Improve data quality pipeline (handle missing values, inconsistencies)
- [ ] **POISS-01**: Fix Poisson calibration to produce realistic scoreline spread (not clustered 1-1, 2-1)
- [ ] **POISS-02**: Revisit per-team attack/defense strength calculation (Dixon-Coles/Bivariate)
- [ ] **POISS-03**: Properly derive match outcome probabilities from goal distributions
- [ ] **MODEL-01**: Implement proper baselines (naive: always 1-1, historical frequencies, bookmaker odds)
- [ ] **MODEL-02**: Add proper scoring rules (log loss, Brier score, ranked probability score)
- [ ] **MODEL-03**: Fix train/validation/test time separation to prevent leakage
- [ ] **MODEL-04**: Improve feature set (form, xG, congestion, home/away strength)
- [ ] **AGENT-01**: Transition to Coordinator-Worker agent architecture
- [ ] **AGENT-02**: Autonomous query/train/predict agent capabilities

### Out of Scope

- Real-time betting integration — focus on batch prediction, not live betting
- Multi-league expansion — stay focused on Argentine leagues for now
- Deep learning models (LSTM, transformers) — keep to tree-based + Poisson for now

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fix Poisson/Distribution first | Scoreline calibration is root cause of generic predictions | — Pending |
| Use odds as baseline/feature | Bookmaker efficiency is the hardest baseline to beat | — Pending |
| Agent architecture | Enables autonomous scaling and cleaner separation of concerns | — Pending |
| Time-series validation | Essential for football data to prevent look-ahead leakage | — Pending |

---
*Last updated: 2026-03-15 after v2.0 initialization*
