# Technology Stack

**Analysis Date:** 2025-03-26

## Languages

**Primary:**
- Python 3.8+ - Core ML pipeline, data processing, web scraping, model training
  - Used throughout: `main.py`, `src/pipeline.py`, `src/stats_engine.py`, model training code

## Runtime

**Environment:**
- Python 3.8+ (supports 3.8 through 3.12)
- Virtual environment required (`.venv` directory exists)

**Package Manager:**
- pip
- Lockfile: requirements.txt (present, pinned versions)

## Frameworks

**Core ML:**
- CatBoost 1.2.0+ (`src/model_engine.py`) - Primary gradient boosting classifier for match outcome prediction
  - Used for binary/ternary classification (Home/Draw/Away)
  - Hyperparameters: 500 iterations, depth=6, learning_rate=0.04
  - Location: `src/config.py` MODEL_PARAMS['catboost']

- LightGBM 4.0.0+ (`src/model_engine.py`) - Alternative gradient boosting classifier (switchable)
  - Same task as CatBoost, configurable via `ML_PREDICTOR_MODEL` env var
  - Hyperparameters: 500 estimators, 32 leaves, learning_rate=0.04
  - Location: `src/config.py` MODEL_PARAMS['lightgbm']

**Data Processing:**
- pandas 2.0.0+ - DataFrames for match history, fixtures, feature tables
  - Core operations in `src/features.py`, `src/data_processing.py`, `parse_reporte_pdfs.py`
  - TimeSeriesSplit cross-validation from sklearn (time-aware train/test splits)

- numpy 1.24.0+ - Numerical computations for Elo/Poisson calculations
  - Matrix operations in `src/stats_engine.py` for Poisson grid calculations
  - Statistical functions for feature engineering

- scipy 1.11.0+ - Statistical distributions
  - `scipy.stats.poisson` - Poisson distribution for goal predictions (`src/stats_engine.py`)
  - `scipy.optimize.brentq` - Root finding for probability calibration

- scikit-learn 1.3.0+ - ML metrics and utilities
  - `accuracy_score`, `log_loss` for cross-validation evaluation (`src/pipeline.py`)
  - `TimeSeriesSplit` for chronological validation (prevents future data leakage)

**Web Scraping:**
- Playwright 1.40.0+ - Modern browser automation for JavaScript-heavy sites
  - Used in `scrape_footystats.py` to bypass anti-scraping protection
  - Handles dynamic content loading (FootyStats tables)
  - Requires: `playwright install chromium`

- Selenium 4.15.0+ - Legacy browser automation
  - Used in `scrape_stats_enhanced.py` for FBref Liga Argentina stats
  - Anti-bot detection handling (Cloudflare, reCAPTCHA, hCaptcha, Turnstile)
  - Requires WebDriver management

- webdriver-manager - Automatic WebDriver installation/management
  - Simplifies Selenium setup (auto-downloads ChromeDriver matching installed Chrome)

- BeautifulSoup4 4.12.0+ - HTML parsing
  - Table extraction in `scrape_footystats.py`, `scrape_tyc.py`, `scrape_sofascore.py`
  - Converts HTML to navigable DOM tree

- lxml 4.9.0+ - XML/HTML parsing backend
  - Faster than built-in html.parser for BeautifulSoup
  - Used in pandas `read_html()` for table parsing

- requests 2.31.0+ - HTTP client
  - Fetch pages in `scrape_tyc.py`, generic web scraping
  - Used for non-JavaScript content

- fake-useragent 1.4.0+ - Dynamic User-Agent generation
  - Bypass simple bot detection in `scrape_stats_enhanced.py`
  - Rotates realistic browser identifiers

**PDF Processing:**
- pdfplumber 0.10.0+ - PDF text/table extraction
  - `parse_reporte_pdfs.py` - Extracts match results from `Reporte/{year}/Resumen F{round}.pdf`
  - Table detection and structured data extraction from Fixture Summary pages

**External APIs:**
- apify-client 1.0.0+ - Apify Actor API integration
  - `scrape_sofascore_apify.py` - Calls pre-built Sofascore scraper actor
  - API endpoint: `https://api.apify.com/` (via client)
  - Dataset and Key-Value Store access for results
  - Auth: `APIFY_API_TOKEN` environment variable

**Testing:**
- pytest 7.4.0+ - Test framework
  - Located: `tests/test_main.py`
  - Tests core math functions: Elo, Poisson, expected goals
  - Run: `pytest tests/test_main.py -v`

## Key Dependencies

**Critical (Direct Usage):**

| Package | Version | Purpose | Core Import |
|---------|---------|---------|------------|
| CatBoost | ≥1.2.0 | Match outcome classification | `from catboost import CatBoostClassifier` |
| LightGBM | ≥4.0.0 | Alternative classifier | `from lightgbm import LGBMClassifier` |
| pandas | ≥2.0.0 | Data manipulation | `import pandas as pd` |
| numpy | ≥1.24.0 | Numerical ops, Poisson grids | `import numpy as np` |
| scipy | ≥1.11.0 | Poisson distribution, optimization | `from scipy.stats import poisson` |
| scikit-learn | ≥1.3.0 | Metrics, TimeSeriesSplit | `from sklearn.model_selection import TimeSeriesSplit` |
| matplotlib | Not in requirements but referenced | Visualization (feature importance) | `import matplotlib.pyplot as plt` |
| Playwright | ≥1.40.0 | Browser automation (FootyStats) | `from playwright.sync_api import sync_playwright` |
| Selenium | ≥4.15.0 | Browser automation (FBref) | `from selenium import webdriver` |
| BeautifulSoup4 | ≥4.12.0 | HTML parsing | `from bs4 import BeautifulSoup` |
| requests | ≥2.31.0 | HTTP requests | `import requests` |
| lxml | ≥4.9.0 | HTML backend | (indirect via pandas) |
| pdfplumber | ≥0.10.0 | PDF extraction | `import pdfplumber` |
| apify-client | ≥1.0.0 | Apify API | `from apify_client import ApifyClient` |

**Infrastructure Dependencies:**
- matplotlib (imported but not listed in requirements) - Used for feature importance visualization
  - Location: `src/pipeline.py` line 16-17 (matplotlib setup, writes PNG files)
  - Uses Agg backend (no display needed): `matplotlib.use("Agg")`

## Configuration

**Environment:**
- `.env.example` exists (structure reference)
- `.venv/` directory for virtual environment
- Configuration stored in `src/config.py`:
  - Elo parameters: `BASE_ELO=1500`, `K_FACTOR=30`, `HOME_ADVANTAGE=65`
  - Poisson parameters: `BASE_GOAL_RATE=1.89`, `MAX_GOALS=8`, `HOME_BOOST=1.22`
  - Model selection: `ML_PREDICTOR_MODEL` env var (defaults to "catboost")
  - Cross-validation: `TRAILING_WINDOW=8` matches for feature engineering

**Build/Dev:**
- No build system (pure Python)
- Development scripts: `setup_venv.ps1` (PowerShell) - Virtual environment setup
- CI/CD: GitHub Actions workflows (.github/ directory)
- Workspace config: `ML_PredictorV2.code-workspace` (VS Code)

## Platform Requirements

**Development:**
- Python 3.8+
- Chrome or Chromium browser (for web scrapers):
  - Selenium: Requires ChromeDriver matching Chrome version
  - Playwright: Auto-downloads browser on first run
- pip package manager
- Recommended: Virtual environment

**Production:**
- Python 3.8+ runtime
- No specific OS requirement (Windows/Linux/macOS)
- Browser dependencies optional (Sofascore/FBref data can use cached JSON)
- Output: CSV files in `src/`, JSON in `src/sofascore_stats.json`, results in `Resultados_*.txt`

**Data Inputs:**
- `data/ARG.csv` - Historical match data
- `Glossary.txt` - Team name mappings
- `partidos.txt` - Upcoming fixtures
- `Reporte/{year}/Resumen F*.pdf` - Official match summaries (optional)
- `src/sofascore_stats.json` - Current standings (from Apify scraper)

## Key Version Constraints

- **numpy 1.24.0+** - Required for recent scipy compatibility
- **pandas 2.0.0+** - API changes in DataFrame operations
- **scikit-learn 1.3.0+** - TimeSeriesSplit improvements
- **CatBoost 1.2.0+** - Stable API for classification
- **Python 3.8** - Minimum for type hints and f-strings (code uses modern Python)

## Dependency Relationships

```
ML Pipeline Stack:
  CatBoost/LightGBM
    └─ scikit-learn (metrics, TimeSeriesSplit)
       └─ numpy (arrays), scipy (stats)
          └─ pandas (DataFrames)

Web Scraping Stack:
  Playwright + Selenium + BeautifulSoup4
    └─ lxml (HTML parsing)
       └─ requests (HTTP)
          └─ fake-useragent (User-Agent rotation)

PDF Processing:
  pdfplumber → pandas (DataFrame conversion)

External APIs:
  apify-client (JSON responses) → pandas (normalization)

Testing:
  pytest → All above stacks for unit tests
```

---

*Stack analysis: 2025-03-26*
