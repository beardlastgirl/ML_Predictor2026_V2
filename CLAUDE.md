# ML_Predictor2026_V2 - CLAUDE.md

## Project Overview

ML_Predictor2026_V2 is an enhanced football match prediction system for Liga Profesional Argentina. It uses Poisson distribution combined with machine learning (LightGBM/CatBoost) to improve prediction accuracy for match outcomes and scorelines.

## Key Innovation: Poisson Distribution Integration

This version introduces Poisson distribution for goal modeling:
- **Expected Goals (xG)**: Calculate xG for each team based on Elo ratings and attack/defense metrics
- **Poisson Probability**: Model goal scores using Poisson distribution
- **Proper Calibration**: Derive match outcome probabilities from goal probability distributions
- **Enhanced Features**: Use Poisson-derived probabilities as ML model features

## Project Structure

```
I:\Scripts\ML_Predictor2026_V2\
├── .venv\                          # Python virtual environment
├── DEV_CONTEXT\                     # Development documentation
├── data\
│   └── ARG.csv                     # Historical match results
├── src\                            # Core source code
│   ├── __init__.py                 # Package marker
│   ├── config.py                   # Constants and hyperparameters
│   ├── data_processing.py          # Data loading and normalization
│   ├── features.py                 # Feature engineering
│   ├── model_engine.py             # ML model and prediction logic
│   ├── stats_engine.py             # Elo and Poisson math
│   ├── utils.py                    # Logging and helpers
│   └── sofascore_stats.json        # Standings from Sofascore
├── tests/                          # Automated test suite
├── main.py                         # Orchestration script (Main Entry Point)
├── scrape_stats_enhanced.py        # FBref statistics scraper (Selenium)
├── scrape_footystats.py            # FootyStats scraper (Playwright)
├── scrape_stats_manual.py          # CDP-based manual browser scraper (FBref/FootyStats)
├── scrape_tyc.py                   # TyC Sports fixtures/results scraper
├── scrape_sofascore_apify.py       # Apify-based Sofascore scraper
├── parse_reporte_pdfs.py           # PDF report parser
├── Glossary.txt                    # Team name mappings
├── run_model.ps1                   # PowerShell menu wrapper
└── requirements.txt                # Python dependencies
```

## Key Files

### Core Engine (Modularized)
- **main.py**: Main orchestration script for the prediction pipeline.
- **src/config.py**: Central configuration for Elo, Poisson, and ML parameters.
- **src/model_engine.py**: Model creation and prediction logic.
- **src/stats_engine.py**: Mathematical implementation of Elo and Poisson distribution.
- **src/features.py**: Chronological trailing-average feature engineering.
- **src/data_processing.py**: Loading and normalizing data from various sources.
- **src/utils.py**: Standard logging and file utility functions.

### Scrapers and Utilities
- **scrape_stats_enhanced.py**: Team statistics scraper from FBref using Selenium.
- **scrape_footystats.py**: Advanced metrics scraper from FootyStats using Playwright.
- **scrape_stats_manual.py**: Multi-site CDP scraper for manual data recovery (FBref/FootyStats).
- **scrape_tyc.py**: Fetches fixtures and recent results from TyC Sports.
- **scrape_sofascore_apify.py**: Apify-based Sofascore scraper (recommended).
- **parse_reporte_pdfs.py**: Extracts match results from PDF reports.

### Configuration
- **Glossary.txt**: Maps team names between sources (TyC, FBref, FootyStats, ARG.csv).

## Data Sources

1. **Historical Data**: `data/ARG.csv` (from football-data.co.uk/argentina.php)
2. **Squad Stats**: FBref via `scrape_stats_enhanced.py`
3. **Advanced Metrics**: FootyStats via `scrape_footystats.py` (xG, PPG)
4. **Fixtures/Results**: TyC Sports via `scrape_tyc.py`
5. **Current Standings**: Sofascore via Apify (`scrape_sofascore_apify.py`)
6. **PDF Reports**: `Reporte/{year}/Resumen F{round}.pdf`

## Running Predictions

### Using PowerShell Menu (Recommended)
```powershell
cd I:\Scripts\ML_Predictor2026_V2
.\run_model.ps1
```

This shows an interactive menu:
```
1 - Parse Reporte PDFs
2 - Scrape FBref Stats
3 - Scrape FootyStats (Playwright)
4 - Scrape Sofascore (via Apify)
5 - Scrape TyC Sports
6 - Manual Scraper (CDP Connection)
7 - Run Main Prediction Model
8 - Run All Data Scrapers + Prediction
0 - Exit
```

Or run directly with option:
```powershell
.\run_model.ps1 -Option 5    # Run main prediction
```

### Manual Execution
```powershell
cd I:\Scripts\ML_Predictor2026_V2
.\.venv\Scripts\Activate.ps1

# Update data
python scrape_stats_enhanced.py
python scrape_sofascore_apify.py
python scrape_tyc.py

# Generate predictions
python main.py
```

## Poisson Distribution Integration

The key enhancement in V2 is the Poisson-based goal modeling:

1. **Calculate Expected Goals (xG)**:
   - BASE_GOAL_RATE = 1.89 (Argentine league average)
   - xG_home = base_rate * home_advantage * attack_factor * defense_factor
   - xG_away = base_rate * attack_factor * defense_factor

2. **Poisson Probability**:
   - P(home_goals = k) = (xG_home^k * e^(-xG_home)) / k!
   - P(away_goals = k) = (xG_away^k * e^(-xG_away)) / k!

3. **Match Outcome Probabilities**:
   - P(Home Win) = sum of P(home_goals > away_goals) for all scorelines
   - P(Draw) = sum of P(home_goals = away_goals) for all scorelines
   - P(Away Win) = sum of P(home_goals < away_goals) for all scorelines

4. **ML Feature Enhancement**:
   - Use Poisson-derived probabilities as additional features
   - Combine with Elo ratings and trailing features

## Current Metrics

- **Model**: CatBoost (default)
- **Time-Series CV Accuracy**: 0.421 (+/- 0.014)
- **Log-Loss**: 1.090
- **Features Used**: 21 (including 10 Poisson-derived features)
- **Training Samples**: 6049 matches

## Apify Scraper for Sofascore Data

The recommended way to get current Sofascore standings:

```powershell
# Option 3 in menu, or:
python scrape_sofascore_apify.py
```

This uses Apify API to fetch current standings from Sofascore. Results are saved to `src/sofascore_stats.json`.

## Testing

Run the automated test suite:
```powershell
python -m pytest tests/test_main.py
```

## Development Guidelines

- NO ANSI colors or escape codes
- NO icons or emojis
- Use plain ASCII characters
- Cross-platform compatible scripts

## Environment Details

- **Virtual Environment**: `.venv` at project root
- **Model Selection**: Set via `ML_PREDICTOR_MODEL` env var (lightgbm/catboost)
- **Python**: 3.8+ required
