# ML_Predictor2026_V2 — Getting Started

<!-- GSD Configuration -->

## Quick Start

```powershell
# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (one-time)
pip install -r requirements.txt

# Generate predictions
python main.py
```

## Prerequisites
- Windows 10/11 with PowerShell 5.1+
- Python 3.8+
- Internet connection (for scraping `ARG.csv` updates and Sofascore standings)

## First-Time Setup

1. **Clone / open** the repository (`C:\Scripts\ML_Predictor2026_V2`).
2. **Create virtual environment**: `python -m venv .venv`
3. **Install**: `pip install -r requirements.txt`
4. **Download latest `data/ARG.csv`** if needed (check timestamp from `https://www.football-data.co.uk/argentina.php`).
5. **Update fixtures**: `python scrape_tyc.py --update-fixtures`

## Weekly Workflow

```powershell
# Option A — PowerShell wrapper (recommended)
.\run_model.ps1 -Option 5

# Option B — Direct Python
python main.py
```

The wrapper (`run_model.ps1`) provides interactive menu options:
- 1: Parse Reporte PDFs
- 2: Scrape FBref Stats
- 3: Scrape Sofascore (via Apify)
- 4: Scrape TyC Sports
- 5: Run Main Prediction Model
- 6: Run All Data Scrapers + Prediction
- 0: Exit

## Expected Output
Predictions written to `Resultados_YYYYMMDD.txt` with calibrated probability distributions (`P(Away)`, `P(Draw)`, `P(Home)`), confidence ratings (Marginal / Moderate / Strong), and market-implied probabilities when available (`EV` calculations against bookmaker odds).

## Cross-References
- `docs/ARCHITECTURE.md` — Pipeline architecture and component graph
- `docs/CONFIGURATION.md` — Hyperparameters (`src/config.py`)
- `docs/TESTING.md` — Running `pytest` (expect 131+ passing tests)
