# ML_Predictor2026_V2: Football Match Prediction

A machine learning pipeline for predicting football match outcomes and scorelines using Poisson distribution, Elo ratings, and gradient boosting. Built for Liga Profesional Argentina (2 championships per year: Apertura / Clausura).

## How It Works

```
Historical Data (ARG.csv)
  + Squad Stats (FBref / FootyStats)
  + Standings (Sofascore via Apify)
  + Fixtures (Partidos.txt)
        ↓
  Elo Ratings + Trailing Stats (8-match window)
  + Poisson xG Features + Shin Odds Extraction
        ↓
  CatBoost/LightGBM (5-fold time-series CV)
  Ensemble: 60% ML + 40% Poisson
        ↓
  PrediccionFechaXX.txt + feature_importance_YYYYMMDD.png
```

**Current metrics:** ~35% CV accuracy (3-class), log-loss ~1.20, 24 features, ~6,200 training matches.

## Setup

```powershell
cd I:\Scripts\ML_Predictor2026_V2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Weekly Workflow

```powershell
.\run_model.ps1
```

Menu options:
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

### Updating Fixtures (Partidos.txt)

Edit `Partidos.txt` manually or run the TyC scraper with the current season URL:

```powershell
python scrape_tyc.py --url "https://www.tycsports.com/..." --fecha "FECHA 10 - 05 al 08/05/2026"
```

If the scraper fails (TyC changes their HTML frequently), update `Partidos.txt` manually:

```
FECHA 10 - 05 al 08/05/2026

River - Boca:
Racing - San Lorenzo:
...

Cantidad de penales cobrados:
Cantidad de expulsados:
Cantidad de goles convertidos:
```

### Updating Historical Data (ARG.csv)

The pipeline auto-checks football-data.co.uk on startup. To update manually:
- Source: https://www.football-data.co.uk/new/ARG.csv
- Target: `data/ARG.csv`

## Season Start Checklist

At the start of each new championship (Apertura or Clausura):

1. Download latest `ARG.csv` from football-data.co.uk
2. Run `python scrape_sofascore_apify.py` to refresh standings
3. Check `[SEASON CHECK]` warnings in pipeline output — these flag promoted/new teams with no historical data
4. Add any new team name variants to `Glossary.txt`
5. Update `Partidos.txt` with the first round fixtures

## Testing

```powershell
python -m pytest tests/ -v
```

Expected: 34+ tests passing.

## Project Structure

```
ML_Predictor2026_V2\
├── data\ARG.csv                    # Historical matches (football-data.co.uk)
├── src\
│   ├── config.py                   # All hyperparameters
│   ├── pipeline.py                 # Orchestration (load → features → train → predict)
│   ├── model_engine.py             # CatBoost/LightGBM + scoreline logic
│   ├── stats_engine.py             # Elo, Poisson, Shin method
│   ├── features.py                 # Trailing stats (exponential decay window)
│   ├── data_processing.py          # Normalization, glossary, fixture parsing
│   ├── data_ingestion.py           # Auto-download ARG.csv
│   ├── validation.py               # Pre-flight data validation
│   └── scraper_utils.py            # Retry decorator, CAPTCHA detection
├── tests\                          # pytest suite (34 tests)
├── Partidos.txt                    # Current round fixtures (edit each week)
├── Glossary.txt                    # Team name mappings across sources
├── main.py                         # Entry point
├── run_model.ps1                   # PowerShell menu wrapper
├── scrape_tyc.py                   # TyC Sports scraper (--url required)
├── scrape_stats_enhanced.py        # FBref via Selenium
├── scrape_footystats.py            # FootyStats via Playwright
├── scrape_stats_manual.py          # FBref/FootyStats via CDP (manual fallback)
├── scrape_sofascore_apify.py       # Sofascore via Apify API
└── parse_reporte_pdfs.py           # PDF report parser
```

## Troubleshooting

**All scores are 1-1:** Goal column mapping issue — check that `Home_GF`/`Away_GF` exist in `ARG.csv` after header mapping.

**`[SEASON CHECK]` warning for a team:** That team has no historical data. Add a name mapping to `Glossary.txt` if it appears under a different name in `ARG.csv`.

**TyC scraper fails:** Update `Partidos.txt` manually. TyC changes their HTML structure frequently.

**Sofascore data stale:** Run `python scrape_sofascore_apify.py` to refresh `src/sofascore_stats.json`.

## Disclaimer

For entertainment purposes only. Not for gambling.
