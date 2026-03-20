# PROJECT_STATUS.md

## Overview

**ML_Predictor2026_V2** is an enhanced football prediction system for Liga Profesional Argentina. The V2 version introduces Poisson distribution for goal modeling combined with machine learning (LightGBM/CatBoost) to improve prediction accuracy.

## Core Components
- **Orchestration Script**: `main.py` (Now a lightweight script that imports modules from `src/`).
- **Core Modules** (`src/`):
  - `config.py`: Centralized configuration.
  - `stats_engine.py`: Elo & Poisson logic.
  - `model_engine.py`: ML model and prediction engine.
  - `features.py`: Chronological feature engineering.
  - `data_processing.py`: Data loading and normalization.
  - `utils.py`: Logging and helpers.
- **Execution Wrapper**: `run_model.ps1` (PowerShell menu-driven script for running individual or all tasks).

## Major Updates

### Modularization (March 2026)
- **Code Separation**: Refactored the monolith `main.py` into a modular package structure in `src/`.
- **Maintainability**: Reduced `main.py` from 1450 lines to ~120 lines, focusing only on orchestration.
- **Improved Imports**: Standardized third-party and local imports across the project.
- **Config Centralization**: Moved all parameters (Elo, Poisson, Model) into `src/config.py`.

### Poisson Distribution Integration (V2 Key Feature - Feb 2026)
- **Expected Goals (xG)**: Calculated from Elo ratings and attack/defense metrics
- **Poisson Probability**: Goal scores modeled using Poisson distribution
- **Proper Calibration**: Match outcome probabilities derived from goal probability distributions
- **Enhanced Features**: Poisson-derived probabilities added as ML model features
- **BASE_GOAL_RATE = 1.89**: Calibrated for low-scoring Argentine league (~1.89 goals/match)

### Enhanced Scraping Strategy (March 2026)
- **FootyStats Integration**: Added `scrape_footystats.py` using Playwright to extract advanced metrics (xG, PPG) from FootyStats.
- **Multi-Site Manual Scraper**: Updated `scrape_stats_manual.py` to support both FBref and FootyStats via Chrome Remote Debugging (CDP).
- **Robustness**: Implemented a multi-source strategy (FBref, FootyStats, Sofascore) to ensure data availability even if one source is blocked.

### Menu-Driven Execution
- **Interactive Menu**: `run_model.ps1` now provides a menu to run scripts independently:
  - 1: Parse Reporte PDFs
  - 2: Scrape FBref Stats
  - 3: Scrape FootyStats (Playwright)
  - 4: Scrape Sofascore (via Apify)
  - 5: Scrape TyC Sports
  - 6: Manual Scraper (CDP Connection)
  - 7: Run Main Prediction Model
  - 8: Run All Data Scrapers + Prediction

### Sofascore Integration
- **Apify Scraper**: Added `scrape_sofascore_apify.py` using Apify API
- **Dual Format Support**: `load_sofascore_data()` handles both:
  - Apify format (30 teams from standings)
  - Manual format (15 teams with normalized names)
- **Current Data**: Sofascore standings now integrated into prediction features

### Bug Fixes
- **Identical xG for all fixtures**: Fixed by adding team-specific trailing stats from historical data
- **Elo Diff Bug**: Fixed `elo_diff = elo_home - elo_home` to `elo_home - elo_away`
- **Draw Prediction Mismatch**: Added handling for draw predictions (ml_pred == 1)
- **All scores 2-1/1-2**: Rewrote score generation to use Poisson most-likely scoreline with confidence threshold
- **Score/Label Mismatch**: Fixed to derive Prediction_Label from actual predicted goals

## Current Metrics (as of 27/02/2026)
- **Model**: CatBoost (default)
- **Time-Series CV Accuracy**: 0.421 (+/- 0.014)
- **Log-Loss**: 1.090
- **Features Used**: 21 (including 10 Poisson-derived features)
- **Training Samples**: 6049 matches

## Feature Importance (Top 5)
1. Away_Elo: 10.4%
2. Elo_Diff: 9.5%
3. Home_Elo: 8.0%
4. Form_Balance: 5.5%
5. Home_Avg_GA: 5.2%

## System Architecture
- **Virtual Environment**: `.venv` at project root
- **Data Sources**: ARG.csv, FBref, FootyStats, TyC, Sofascore (Apify), PDF Reports
- **Model Selection**: Environment variable controlled (LightGBM/CatBoost)
- **Testing**: pytest-based validation

## Known Challenges
- **Scraper Fragility**: Web scrapers sensitive to DOM changes - mitigated with triple scraper strategy (FBref, FootyStats, Sofascore)
- **Manual Mapping**: New teams require manual entries in Glossary.txt
- **Browser Dependencies**: CDP scraper requires Chrome with DevTools protocol

## Operational Status
- **Weekly Predictions**: Running successfully with menu-driven execution
- **Data Sources**: All scrapers functional (FBref, FootyStats, TyC, Sofascore via Apify)
- **Model Performance**: Stable with ~42% accuracy on 3-class problem
- **Documentation**: Up-to-date with March 2026 scraping enhancements
