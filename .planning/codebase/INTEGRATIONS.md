# External Integrations

**Analysis Date:** 2026-03-15

## APIs & External Services

**Sports Data Providers:**
- **FBref** - Team statistics (goals for/against, match results)
  - URL: `https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats`
  - Scraper: `scrape_stats_enhanced.py` (Selenium with anti-bot handling)
  - Anti-bot: Cloudflare DDoS, Turnstile, reCAPTCHA, hCaptcha detection
  - Manual intervention supported for CAPTCHA solving

- **FootyStats** - Advanced metrics (xG, PPG, possession stats)
  - URL: `https://footystats.org/argentina/primera-division`
  - Scraper: `scrape_footystats.py` (Playwright)
  - Scraper: `scrape_stats_manual.py` (CDP Chrome Remote Debugging)

- **Sofascore** - Current league standings
  - URL: `https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155`
  - Scraper: `scrape_sofascore_apify.py` (Apify API)
  - Apify Actor: `azzouzana/sofascore-scraper-pro`
  - Output: `src/sofascore_stats.json`

- **TyC Sports** - Fixtures and recent results
  - URL: `https://www.tycsports.com/liga-profesional-de-futbol/`
  - Scraper: `scrape_tyc.py` (requests + BeautifulSoup)
  - Output: `partidos.txt`

## Data Storage

**Databases:**
- None - File-based storage only
- Historical data: `data/ARG.csv` (from football-data.co.uk)
- Connection: N/A

**File Storage:**
- Local filesystem for all data
- Historical matches: `data/ARG.csv` (~837KB, 6000+ matches)
- Standings cache: `src/sofascore_stats.json`
- Scraped stats: `src/results*.csv`, `src/stats*.csv`
- Predictions output: `Resultados_{YYYYMMDD}.txt`

**Caching:**
- Rate limiting in `scrape_stats_manual.py` (once per day check)
- No Redis or external cache

## Authentication & Identity

**Auth Provider:**
- Custom/API keys only
- Apify API token: `APIFY_API_TOKEN` environment variable
- Default token embedded in `scrape_sofascore_apify.py` (line 32)

## Monitoring & Observability

**Error Tracking:**
- None - Console logging only
- Custom logging via `src/utils.py`: `log_info`, `log_ok`, `log_error`, `log_warning`

**Logs:**
- stdout console output
- No file logging
- No structured logging

## CI/CD & Deployment

**Hosting:**
- Local execution only
- No cloud deployment

**CI Pipeline:**
- None configured
- Manual execution via PowerShell menu (`run_model.ps1`)

## Environment Configuration

**Required env vars:**
- `ML_PREDICTOR_MODEL` - Model selection (lightgbm/catboost)
- `APIFY_API_TOKEN` - Apify API authentication

**Secrets location:**
- `.env.example` template present but no `.env` file committed
- Apify token defaults to embedded value in code (security concern)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Data Flow Integrations

**PDF Reports:**
- Input: `Reporte/{year}/Resumen F{round}.pdf`
- Parser: `parse_reporte_pdfs.py` using pdfplumber
- Extracts: Match results for historical data

**Team Name Mapping:**
- Glossary: `Glossary.txt` (186 team name mappings)
- Format: `Source Name -> Normalized Name`
- Used by all scrapers for consistent team identification

---

*Integration audit: 2026-03-15*
