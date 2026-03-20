# ML_Predictor2026_V2: Football Match Prediction with Poisson Distribution

A machine learning pipeline for predicting football match outcomes using Poisson distribution, historical data, squad statistics, and dynamic Elo ratings. Built specifically for Liga Profesional Argentina.

## Key Innovation: Poisson Distribution Integration

This version introduces a more sophisticated approach to goal prediction:

1. **Expected Goals (xG) Calculation**: Uses Elo ratings and attack/defense metrics to estimate expected goals for each team
2. **Poisson Distribution**: Models goal scoring as a Poisson process for accurate probability calculations
3. **Proper Outcome Calibration**: Derives match outcome probabilities from goal distributions
4. **Enhanced ML Features**: Uses Poisson-derived probabilities as additional features for the gradient boosting model

## Setup

### Prerequisites
- Windows 10/11 with PowerShell 5.1+
- Python 3.8+ installed
- Internet connection for scraping data

### Installation

```powershell
# Navigate to project directory
cd C:\Scripts\ML_Predictor2026_V2

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
Target: C:\\Scripts\\ML_Predictor2026_v2\\data\\ARG.csv
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
.\run_model.ps1
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
.\run_model.ps1 -Option 5  # Run main prediction
.\run_model.ps1 -Option 6  # Run everything
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

## How It Works

### Poisson-Based Goal Modeling

The system calculates expected goals (xG) for each team and uses Poisson distribution to model scoring probabilities:

```
xG_home = base_rate * home_advantage * attack_home * defense_away
xG_away = base_rate * attack_away * defense_home

P(k goals) = (xG^k * e^(-xG)) / k!
```

Match outcome probabilities are derived by summing over all possible scorelines.

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
5. **Home Advantage**: Built into calculations

## Project Structure

```
ML_Predictor2026_V2\
├── .venv\                      # Virtual environment
├── data\
│   └── ARG.csv                 # Historical matches
├── src\                        # Source code and data
│   ├── __init__.py             # Package marker
│   ├── config.py               # Constants and hyperparameters
│   ├── data_processing.py      # Data loading and normalization
│   ├── features.py             # Feature engineering
│   ├── model_engine.py         # ML model and prediction logic
│   ├── stats_engine.py         # Elo and Poisson math
│   ├── utils.py                # Logging and helpers
│   └── sofascore_stats.json    # Scraped statistics
├── tests\                      # Test suite
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
python -m pytest tests/test_main.py
```

## Troubleshooting

### Error: "No files match pattern src/results*.csv"
Run the scraper: `python scrape_stats_enhanced.py`

### Error: "Fixtures file not found"
Run: `python scrape_tyc.py --update-fixtures`

## Disclaimer

Predictions are for entertainment purposes only. Do not use for gambling.

## License

Personal project for friends' entertainment. No commercial use intended.
