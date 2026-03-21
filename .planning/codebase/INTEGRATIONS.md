# External Integrations

**Analysis Date:** 2025-03-26

## APIs & External Services

### Sofascore (via Apify)

- **Service:** Sofascore Liga Profesional Argentina standings
- **Primary Script:** `scrape_sofascore_apify.py`
- **URL:** `https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155`
- **Method:** Apify Actor (cloud-based browser automation)
- **Data Retrieved:**
  - Team standings (position, points, wins/draws/losses)
  - Goals for/against
  - Match results and stats
- **SDK/Client:** `apify-client` 1.0.0+
- **Auth:** 
  - Environment variable: `APIFY_API_TOKEN`
  - Retrieved from Apify dashboard (account-specific token)
  - Passed to: `ApifyClient(API_TOKEN)` constructor
- **Endpoints Used:**
  - Actor endpoint: `client.actor("azzouzana/sofascore-scraper-pro").call(run_input)`
  - Dataset iteration: `client.dataset(dataset_id).iterate_items()`
  - Key-Value Store: `client.key_value_store(STORE_ID).get_record("STANDINGS")`
- **Data Format:**
  - Input: JSON with startUrls array
  - Output: JSON with team objects containing: `name`, `position`, `points`, `played`, `won`, `drawn`, `lost`, `goalsFor`, `goalsAgainst`, `goalDifference`
  - Processed into: `src/sofascore_stats.json` (timestamp, source metadata, normalized teams)
- **Rate Limiting:** Handled by Apify (depends on actor credits/quotas)
- **Error Handling:**
  - Lines 95-96: Token validation before API calls
  - Lines 111-123: Try/except for actor execution
  - Lines 137-145: Fallback to KV store if dataset empty
  - Retry logic: None implemented (single attempt per run)
- **Failure Mode:** Returns empty JSON if Apify fails; pipeline continues with stale `sofascore_stats.json`
- **Performance:** ~1 minute per run (actor initialization + scraping)

### FBref (Liga Profesional Argentina Stats)

- **Service:** Football Reference league statistics (Belgian-based, detailed stats)
- **Primary Script:** `scrape_stats_enhanced.py`
- **URL:** `https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats`
- **Method:** Selenium browser automation (detects and handles anti-bot)
- **Data Retrieved:**
  - League tables (season standings)
  - Advanced stats: xG, xGA, Pass completion, Possession, etc.
  - Team statistics (CSV format)
- **Client:** Selenium WebDriver (Chrome) + BeautifulSoup4
- **Auth:** None required (public site, no authentication)
- **Anti-Bot Detection Handling:**
  - Cloudflare challenge detection (lines 83-100 in scrape_stats_enhanced.py)
  - reCAPTCHA detection (lines 101-120)
  - hCaptcha detection (lines 121-135)
  - Turnstile detection (lines 136-150)
  - Manual intervention prompts for user to solve CAPTCHA in browser
  - Optional flag `--force-continue-after-solve` to auto-retry when URL changes
- **Data Format:**
  - HTML tables → BeautifulSoup parsing → pandas DataFrame
  - Output: CSV files named `fbref_[table_type]_[date]_[round].csv`
  - Example: `src/fbref_league_table_20260307_10.csv`
  - Columns: Squad, Rk (rank), MP, W, D, L, GF, GA, GD, Pts, etc.
- **Rate Limiting:**
  - Implicit: Playwright page load timeout (30s default, configurable)
  - Between requests: 2-5s random delays (lines 245-250)
  - Headless mode available to reduce detection
- **Error Handling:**
  - Try/except for WebDriver initialization (lines 283-295)
  - Page load validation checks (lines 301-320)
  - Table detection with fallback (lines 322-340)
  - CAPTCHA detection loops with user prompts
- **Failure Mode:** Halts on CAPTCHA if manual solve not provided; otherwise skips failed round
- **Performance:** 5-20 seconds per table (depends on page complexity)
- **Table Types Extracted:**
  - League table (team standings)
  - Advanced stats (expected goals, pass metrics)
  - Other advanced (possession, defensive actions)

### FootyStats (Argentina Primera Division)

- **Service:** FootyStats detailed league statistics
- **Primary Script:** `scrape_footystats.py`
- **URL:** `https://footystats.org/argentina/primera-division`
- **Method:** Playwright browser automation (real Chrome browser)
- **Data Retrieved:**
  - Team statistics tables (Goals, Assists, xG, etc.)
  - League standings
  - Player-level stats (aggregated by team)
- **Client:** Playwright 1.40.0+ (sync API)
- **Auth:** None required (public site)
- **Anti-Bot Detection Handling:**
  - Anti-scraping protections bypassed via real browser (JavaScript execution)
  - No CAPTCHA handling (relies on legitimate browser automation)
- **Data Format:**
  - Dynamic HTML tables (loaded via JavaScript)
  - BeautifulSoup parsing of rendered DOM
  - Output: CSV files named `footystats_[stat_type]_[date]_[team_id].csv`
  - Example: `src/footystats_metrics_20260320_1.csv`
  - Columns: Squad, Goals, Assists, Shots, xG, etc. (varies by table)
- **Rate Limiting:**
  - Page load timeout: 30s default (lines 87-100)
  - Wait between tables: 3s (lines 180-190)
  - No documented request throttling
- **Error Handling:**
  - Try/except for Playwright initialization (lines 120-140)
  - Page visibility checks (lines 155-165)
  - Table extraction with fallback to empty DataFrame
  - Logging via `src/utils` (log_error, log_warning)
- **Failure Mode:** Skips failed tables; continues with others
- **Performance:** 10-30 seconds per run (browser startup + multiple tables)
- **Team Identifiers:** Numeric IDs (1-27) for 27 teams in Liga Profesional

### TyC Sports (Fixture Data)

- **Service:** TyC Sports fixture/result data (Argentine TV network)
- **Primary Script:** `scrape_tyc.py`
- **URL:** Multiple URLs (fixtures, results pages)
- **Method:** HTTP requests + BeautifulSoup (no JavaScript)
- **Data Retrieved:**
  - Upcoming fixtures (teams, dates, times)
  - Historical results (scores, teams)
  - Match metadata (round, venue)
- **Client:** requests library + BeautifulSoup4
- **Auth:** None required (public site, basic request headers)
- **Headers Used:**
  - User-Agent: Chrome-like string (line 53-55)
  - Accept: HTML + XHTML (line 54)
  - Accept-Language: es-AR (Spanish, Argentina)
  - Timeout: 30s per request
- **Data Format:**
  - HTML markup with score patterns: "Team A 2 - 1 Team B"
  - Regex patterns: `(\d+)\s*-\s*(\d+)` for scores
  - Output: Varies (could be CSV or JSON)
  - Columns expected: Date, Home, Away, GF, GA, Round
- **Rate Limiting:**
  - Single timeout per URL (30s)
  - No retry logic on failure
- **Error Handling:**
  - Try/except for HTTP fetch (lines 49-71)
  - Raises HTTPError on 4xx/5xx
  - Logs: log_error on exception
- **Failure Mode:** Raises exception; caller must handle
- **Performance:** <2 seconds per URL

## Data Storage

**Databases:** None - All data is file-based

**File Storage:**

| Storage | Format | Purpose | Path | Update Frequency |
|---------|--------|---------|------|-----------------|
| Historical matches | CSV | Historical results for training | `data/ARG.csv` | Manual/weekly |
| Sofascore standings | JSON | Current team standings | `src/sofascore_stats.json` | On scrape (Apify) |
| FBref stats | CSV | Advanced league metrics | `src/fbref_*.csv` | On scrape (Selenium) |
| FootyStats tables | CSV | Detailed team stats | `src/footystats_*.csv` | On scrape (Playwright) |
| Fixtures | TXT | Upcoming matches to predict | `partidos.txt` | Manual input |
| PDF reports | PDF | Official match summaries | `Reporte/{year}/Resumen F*.pdf` | External source |
| Model results | TXT | Prediction output | `Resultados_*.txt`, `Resultados_Simple_*.txt` | Per prediction run |
| Feature importance | PNG | Model visualization | `feature_importance_*.png` | Per training run |

**Local Filesystem:**
- `src/` - Data cache and intermediate files
- `data/` - Historical data input
- `Reporte/` - PDF fixture reports
- `.venv/` - Virtual environment (dependencies)
- `__pycache__/`, `catboost_info/`, `.pytest_cache/` - Cache directories

**Caching:**
- None implemented - Pipeline recalculates features each run
- Sofascore: KV store caching (Apify-side)
- FBref/FootyStats: CSV files cached locally by timestamp

## Authentication & Identity

**Auth Provider:** None - No central auth system

**Public APIs:**
- Sofascore: Apify Actor (requires Apify account + token)
- FBref: Public (no auth)
- FootyStats: Public (no auth)
- TyC Sports: Public (no auth)

**Secret Management:**
- Environment variables (`.env` file, not committed):
  - `APIFY_API_TOKEN` - Apify API key
  - `ML_PREDICTOR_MODEL` - Model selection (optional)
- Glossary.txt is committed (team name mappings, no secrets)

## Monitoring & Observability

**Error Tracking:** None (no external service)

**Logging:** Console-only (no centralized logging)
- Utility functions: `src/utils.py`
  - `log_info()` - Informational messages (prefix: `[INFO]`)
  - `log_ok()` - Success messages (prefix: `[OK]`)
  - `log_error()` - Errors (prefix: `[ERROR]`)
  - `log_warning()` - Warnings (prefix: `[WARNING]`)
- Output: Printed to stdout/stderr during execution
- Logs in: `scrape_sofascore_apify.py`, `scrape_footystats.py`, `scrape_tyc.py`, `parse_reporte_pdfs.py`

## CI/CD & Deployment

**Hosting:** Local/on-premise only (not cloud-hosted)

**CI Pipeline:**
- GitHub Actions workflows present (`.github/` directory)
- Workspace file: `ML_PredictorV2.code-workspace` (VS Code config)
- No automated deployment observed

**Run Methods:**
- Direct Python: `python main.py`
- PowerShell scripts:
  - `setup_venv.ps1` - Environment setup
  - `run_model.ps1` - Execute model
  - `_UpdateGit2026_V2.bat` - Git operations
  - `_Run_ClaudeCode_ollama.cmd` - AI integration

## Environment Configuration

**Required Environment Variables:**

| Variable | Purpose | Source | Example |
|----------|---------|--------|---------|
| `APIFY_API_TOKEN` | Sofascore scraper auth | Apify dashboard | `eyJhbGc...` (JWT token) |
| `ML_PREDICTOR_MODEL` | Model selection | Optional, defaults to "catboost" | `lightgbm` or `catboost` |

**Secrets Location:**
- `.env` file (git-ignored, not in repo)
- `.env.example` - Template structure provided
- Tokens stored locally; never committed to git

**Required Input Files:**
- `Glossary.txt` - Team name mappings (committed)
- `data/ARG.csv` - Historical match data (committed)
- `partidos.txt` - Fixtures to predict (manual/external)

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None (no external callbacks from this system)

## API Usage Patterns

**Sofascore (Apify):**
```python
# Authentication
client = ApifyClient(API_TOKEN)

# Execute scraper
run = client.actor("azzouzana/sofascore-scraper-pro").call(run_input=run_input)

# Fetch results
dataset_id = run.get("defaultDatasetId")
items = [item for item in client.dataset(dataset_id).iterate_items()]

# Alternative: Key-Value Store
store = client.key_value_store(STORE_ID)
record = store.get_record("STANDINGS")
standings_data = record.get("value")
```

**FBref (Selenium):**
```python
# Browser setup
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Navigate
driver.get("https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats")

# Extract tables
page_source = driver.page_source
soup = BeautifulSoup(page_source, 'html.parser')
tables = soup.find_all('table')
```

**FootyStats (Playwright):**
```python
# Browser automation
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://footystats.org/argentina/primera-division")
    
    # Extract rendered content
    tables = page.locator('table').all()
```

**TyC Sports (Requests):**
```python
# HTTP request
headers = {'User-Agent': 'Mozilla/5.0...'}
response = requests.get(url, headers=headers, timeout=30)
html = response.text

# Parse
soup = BeautifulSoup(html, 'html.parser')
```

## Data Format Specifications

**Sofascore JSON Output (`src/sofascore_stats.json`):**
```json
{
  "scraped_at": "2025-03-26T10:30:00",
  "source": "sofascore",
  "source_type": "apify",
  "url": "https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155",
  "teams": [
    {
      "name": "BOCA JUNIORS",
      "normalized": "BOCA JUNIORS",
      "position": 1,
      "points": 45,
      "played": 15,
      "won": 14,
      "drawn": 1,
      "lost": 0,
      "goals_for": 38,
      "goals_against": 5
    }
  ],
  "standings": [...]
}
```

**FBref CSV Output (`src/fbref_league_table_*.csv`):**
```csv
Squad,Rk,MP,W,D,L,GF,GA,GD,Pts,Pts/MP
BOCA JUNIORS,1,15,14,1,0,38,5,+33,43,2.87
```

**FootyStats CSV Output (`src/footystats_metrics_*.csv`):**
```csv
Squad,Goals,Assists,Shots,xG,xA,Pass%
BOCA JUNIORS,38,12,156,35.2,9.8,78.5
```

**Historical Data CSV (`data/ARG.csv`):**
```csv
Date,Home,Away,Res,GF,GA
2025-02-01,BOCA JUNIORS,RIVER PLATE,2,2,1
2025-02-08,SAN LORENZO,RIVER PLATE,1,1,1
```

**Fixtures File (`partidos.txt`):**
```
BOCA JUNIORS vs RIVER PLATE
INDEPENDIENTE vs SAN LORENZO
VELEZ vs TALLERES
```

## Integration Points in Code

| Component | Integration | File | Lines |
|-----------|-----------|------|-------|
| Sofascore normalization | Team name mapping to glossary | `scrape_sofascore_apify.py` | 35-79 |
| FBref table extraction | Selenium WebDriver management | `scrape_stats_enhanced.py` | 83-150 |
| FootyStats scraping | Playwright page interaction | `scrape_footystats.py` | 87-250 |
| TyC Sports parsing | BeautifulSoup HTML parsing | `scrape_tyc.py` | 73-120 |
| PDF extraction | pdfplumber table detection | `parse_reporte_pdfs.py` | 100-200 |
| Data normalization | Glossary-based team mapping | `src/data_processing.py` | 39-61 |
| Pipeline orchestration | Load all sources | `src/pipeline.py` | 65-100 |

---

*Integration audit: 2025-03-26*
