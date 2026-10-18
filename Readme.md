# ML_Predictor2026_V2: Football Match Prediction with Poisson Distribution

A machine learning pipeline for predicting football match outcomes using Poisson distribution, historical data, squad statistics, and dynamic Elo ratings. Built specifically for Liga Profesional Argentina.

## Key Innovation: Probability Engine & Expected Value (EV) Analysis

As of Phase 3.0, the system operates as a **probability distribution engine** rather than a hard 1X2 classifier. Mathematical and empirical analysis demonstrated that hard argmax classification cannot reliably isolate draws in Argentine football due to structural home advantage (mean home goals ~1.3 vs away goals ~0.97) and high match variance.

Instead of guessing a single forced outcome, the engine outputs full outcome probability distributions:
- **Calibrated Probability Triple**: `P(Away)`, `P(Draw)`, `P(Home)` following canonical encoding (0=Away, 1=Draw, 2=Home).
- **Market Implied Probabilities**: Shin-method de-vigged bookmaker probabilities (when odds are provided).
- **Confidence Rating**: Categorizes top picks as Marginal, Moderate, or Strong.
- **Expected Value (EV) Focus**: Designed for value detection against bookmaker markets (`EV = (P_model * Decimal_Odds) - 1.0`) rather than brittle hard classifications.

### Core Mathematical Components:
1. **Expected Goals (xG) Calculation**: Uses Elo ratings and attack/defense metrics to estimate expected goals for each team
2. **Poisson Distribution**: Models goal scoring as a Poisson process for accurate probability calculations
3. **Shin Method**: Extracts true probabilities from bookmaker odds to correct for market bias and calculate market-implied probabilities
4. **Enhanced ML Features**: Uses Poisson and Shin probabilities as features for gradient boosting (CatBoost)
5. **Tournament-Aware CV**: Cross-validation that respects season/tournament boundaries to prevent lookahead leakage

## Setup

### Prerequisites
- Windows 10/11 with PowerShell 5.1+
- Python 3.8+ installed
- Internet connection for scraping data

### Installation

```powershell
# Navigate to project directory (Example: C:\Scripts\ML_Predictor2026_V2)
cd "C:\Scripts\ML_Predictor2026_V2"

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Copy Data Files
- Check the "Last updated" timestamp from https://www.football-data.co.uk/argentina.php
- Download and overwrite data/ARG.csv only if the web version is newer than local file
- Verify the update with confirmation message and file properties
Target: data\ARG.csv
Source: https://www.football-data.co.uk/new/ARG.csv

- `data/ARG.csv` - Historical match data
- `Glossary.txt` - Team name mappings

## Usage

### Standard Weekly Workflow

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Update data (choose one method)
python scrape_stats_enhanced.py   # Automated (may encounter CAPTCHAs)
python scrape_stats_manual.py     # Manual browser (recommended)

# Update fixtures
python scrape_tyc.py

# Generate predictions
python main.py
```

### Using PowerShell Wrapper

```powershell
.
un_model.ps1
```

This opens an interactive menu:

```
1 - Parse Reporte PDFs
2 - Scrape FBref Stats
3 - Scrape Sofascore (via Apify)
4 - Scrape TyC Sports
5 - Run Main Prediction Model
6 - Run All Data Scrapers + Prediction
0 - Exit
```

Or run with option directly:
```powershell
.
un_model.ps1 -Option 5  # Run main prediction
.
un_model.ps1 -Option 6  # Run everything
```

### Apify Scraper (Sofascore)

To scrape current standings from Sofascore:

```powershell
python scrape_sofascore_apify.py
```

This uses the Apify API to fetch current tournament standings and saves to `src/sofascore_stats.json`.

This opens an interactive menu:

```
1 - Parse Reporte PDFs
2 - Scrape FBref Stats
3 - Scrape Sofascore (via Apify)
4 - Scrape TyC Sports
5 - Run Main Prediction Model
6 - Run All Data Scrapers + Prediction
0 - Exit
```

Or run with option directly:
```powershell
.\run_model.ps1 -Option 5  # Run main prediction only
```

### Prediction Output Format

Predictions are written to `Resultados_YYYYMMDD.txt` and output to the terminal as calibrated probability distributions:

```text
Match: Boca Juniors vs River Plate
P(Away): 26.4% | P(Draw): 28.1% | P(Home): 45.5%
Market Implied: [If available]
Top Pick: Home (Marginal)
---
```

## How It Works

### Poisson-Based Goal Modeling

The system calculates expected goals (xG) for each team and uses Poisson distribution to model scoring probabilities:

```
xG_home = base_rate * home_advantage * attack_home * defense_away
xG_away = base_rate * attack_away * defense_home

P(k goals) = (xG^k * e^(-xG)) / k!
```

Match outcome probabilities are derived by summing over all possible scorelines.

### Shin Method for Market Probability Extraction

The Shin method assumes a proportion of "insider traders" in betting markets and recovers true outcome probabilities from bookmaker odds:

```
pi_i = (1-z)p_i + z*sqrt(p_i)
```

This corrects for the bookmaker's overround and provides calibrated probabilities for use as features.

### Tournament-Aware Cross-Validation

Cross-validation splits respect tournament/season boundaries to prevent lookahead leakage. Features for validation fold t are computed only from matches prior to time t.

### Data Pipeline

```
Historical Data (ARG.csv) --> main.py
Squad Stats (FBref) --> scrape_stats_enhanced.py --> src/results*.csv
Advanced Stats (FootyStats) --> scrape_footystats.py --> src/footystats*.csv
Fixtures (TyC Sports) --> scrape_tyc.py --> partidos.txt
PDF Reports --> parse_reporte_pdfs.py --> ARG.csv
```

### Features Used

1. **Elo Ratings**: Dynamic team strength ratings
2. **Attack/Defense Metrics**: From current season statistics (FBref, FootyStats, Sofascore)
3. **Trailing Averages**: Last 8 matches performance
4. **Poisson Probabilities**: xG-based outcome probabilities
5. **Shin Probabilities**: Bookmaker-derived true probabilities
6. **Home Advantage**: Built into calculations
7. **Sofascore Features**: Current standings, ratings, goal differences

## Project Structure

```
ML_Predictor2026_V2\
├── .venv\                      # Virtual environment
├── data\
│   └── ARG.csv                 # Historical matches
├── src\                        # Source code and data
│   ├── __init__.py             # Package marker
│   ├── config.py               # Constants and hyperparameters
│   ├── cv_split.py             # Tournament-aware cross-validation
│   ├── data_processing.py      # Data loading and normalization
│   ├── data_gateway.py         # Data access facade (planned)
│   ├── entity_resolver.py      # Canonical team name resolution (planned)
│   ├── features.py             # Feature engineering
│   ├── model_engine.py         # ML model and prediction logic
│   ├── normalization.py        # Shared team name normalization (planned)
│   ├── pipeline.py             # End-to-end pipeline orchestration
│   ├── stats_engine.py         # Elo, Poisson, and Shin math
│   ├── utils.py                # Logging and helpers
│   ├── validation.py           # Data validation layer
│   └── sofascore_stats.json    # Scraped statistics
├── tests\                      # Test suite (80 tests)
│   ├── test_golden_math.py     # Golden math regression tests
│   ├── test_main.py            # Unit tests for core functions
│   ├── test_pipeline_integration.py  # End-to-end integration tests
│   └── test_scraper_utils.py   # Scraper utility tests
├── main.py                     # Orchestration script
├── scrape_stats_enhanced.py    # FBref Selenium scraper
├── scrape_footystats.py        # FootyStats Playwright scraper
├── scrape_stats_manual.py      # Manual browser CDP scraper (FBref/FootyStats)
├── scrape_tyc.py               # TyC Sports scraper
├── parse_reporte_pdfs.py       # PDF parser
├── Glossary.txt                # Team name mappings
├── run_model.ps1               # PowerShell menu wrapper
└── requirements.txt            # Dependencies
```

## Testing

```powershell
# Run all tests (80 tests)
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_golden_math.py -v       # 17 golden math tests
python -m pytest tests/test_main.py -v              # 29 unit tests
python -m pytest tests/test_pipeline_integration.py -v  # 19 integration tests
python -m pytest tests/test_scraper_utils.py -v     # 15 scraper tests
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every PR:
- pytest test suite (80 tests)
- pip-audit for dependency vulnerabilities
- Artifact tracking check (prevents committing generated files)

## Current Baseline Metrics (2026-09-26)

- **Historical Matches Processed**: 6,416
- **Surviving Training Samples**: 6,416 (cold-start imputation; was 340)
- **5-Fold Tournament-Aware CV Accuracies**: ~0.34 mean (+/- 0.07)
- **5-Fold Tournament-Aware CV Log Losses**: ~1.25 mean
- **Dynamic Naive Baseline Log Loss**: ~1.08
- **Bookmaker Baseline Log Loss**: ~1.04

Note: Model performs at naive baseline level (per audit findings). Objective clarification needed before hyperparameter tuning.

## Troubleshooting

### Error: "No files match pattern src/results*.csv"
Run the scraper: `python scrape_stats_enhanced.py`

### Error: "Fixtures file not found"
Run: `python scrape_tyc.py --update-fixtures`

## Disclaimer

Predictions are for entertainment purposes only. Do not use for gambling.

## License

Personal project for friends' entertainment. No commercial use intended.
