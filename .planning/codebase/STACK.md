# Technology Stack

**Analysis Date:** 2026-03-15

## Languages

**Primary:**
- Python 3.8+ - Core language for all ML pipelines, scrapers, and data processing

**Secondary:**
- PowerShell - Build scripts and menu wrappers (`run_model.ps1`, `setup_venv.ps1`)

## Runtime

**Environment:**
- Python 3.8+ virtual environment (`.venv/`)
- Windows 11 Pro development environment

**Package Manager:**
- pip
- Lockfile: Not present (no `requirements.lock` or `Pipfile.lock`)

## Frameworks

**Core:**
- pandas 2.0+ - Data manipulation and CSV processing
- numpy 1.24+ - Numerical computations for Poisson distribution
- scipy 1.11+ - Statistical functions (Poisson PMF)

**Testing:**
- pytest 7.4+ - Unit test framework
- Location: `tests/test_main.py`

**Build/Dev:**
- playwright - Browser automation for FootyStats scraping
- selenium 4.15+ - Browser automation for FBref scraping
- webdriver-manager - Automatic ChromeDriver management

## Key Dependencies

**Critical:**
- catboost 1.2+ - Primary ML model (default)
- lightgbm 4.0+ - Alternative ML model
- scikit-learn 1.3+ - TimeSeriesSplit cross-validation, metrics

**Infrastructure:**
- beautifulsoup4 4.12+ - HTML parsing for scrapers
- lxml 4.9+ - XML/HTML parser backend
- requests 2.31+ - HTTP client for web scraping
- apify-client 1.0+ - Apify API for Sofascore data
- pdfplumber 0.10+ - PDF report parsing
- fake-useragent 1.4+ - Dynamic User-Agent generation
- websocket-client - CDP WebSocket communication

## Configuration

**Environment:**
- Environment variables via `.env.example` (template only)
- Model selection via `ML_PREDICTOR_MODEL` env var (lightgbm/catboost)
- Apify token via `APIFY_API_TOKEN` env var (defaults to embedded token in code)

**Build:**
- `requirements.txt` - All dependencies listed
- No pyproject.toml or setup.py

## Platform Requirements

**Development:**
- Chrome browser installed (for Selenium/Playwright scrapers)
- ChromeDriver matching browser version
- `.venv/` virtual environment at project root
- PowerShell execution policy for running scripts

**Production:**
- Windows deployment target
- Requires Chrome for web scraping components
- Apify API access for Sofascore data

## Data Processing Stack

**CSV Processing:**
- pandas `read_csv` for historical data (`data/ARG.csv`)
- Custom parsing for fixtures (`partidos.txt`)

**JSON Processing:**
- Standard `json` module for Sofascore data (`src/sofascore_stats.json`)

**PDF Processing:**
- pdfplumber for match result PDFs (`Reporte/{year}/Resumen F{round}.pdf`)

---

*Stack analysis: 2026-03-15*
