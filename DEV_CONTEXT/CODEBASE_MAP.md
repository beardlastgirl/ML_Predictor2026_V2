# ML_Predictor2026_V2 - Comprehensive Codebase Map

**Last Updated:** 2026-03-21
**Language:** Python 3.8+
**Target Domain:** Liga Profesional Argentina Football Match Predictions

---

## 1. Architecture Overview

### System Pattern: Data Pipeline + ML Ensemble + Poisson Enhancement

The system follows a **sequential data pipeline architecture** with three distinct phases:

```
DATA COLLECTION → FEATURE ENGINEERING → MODEL TRAINING → PREDICTION OUTPUT
     ↓
   Scrapers
   (TyC, FBref, Sofascore, Footystats, PDFs)
     ↓
   Historical Data (ARG.csv)
     ↓
   Glossary Normalization
   
FEATURE ENGINEERING
   ↓
   Elo Rating Calculation
   + Trailing Statistics (8-match window)
   + Poisson Distribution Features
   + Shin Method Probability Extraction
   ↓
   Feature Matrix (24 features total)

MODEL TRAINING
   ↓
   CatBoost/LightGBM Classifier
   (Time-Series 5-fold CV)
   + Class weight balancing
   ↓
   60% ML + 40% Poisson Ensemble Blend

PREDICTION
   ↓
   Scoreline + Outcome Labels
   + Feature Importance
   + Results Files
```

### Key Innovation: Poisson Distribution Integration

Unlike purely ML-based approaches, this system uses **Poisson distribution modeling** to:
1. Calculate Expected Goals (xG) for each team from Elo + attack/defense metrics
2. Model goal probability as Poisson process: P(k goals) = (λ^k * e^-λ) / k!
3. Derive match outcome probabilities from goal distributions
4. Calibrate probabilities to league averages (adjust draw bias)
5. Blend with ML probabilities (60% ML / 40% Poisson) for final prediction

---

## 2. Component Relationships & Data Flow

### Data Sources (External Inputs)

| Source | File | Purpose | Scraper |
|--------|------|---------|---------|
| Football-Data.co.uk | `data/ARG.csv` | Historical matches (results + odds) | Manual download |
| TyC Sports | `partidos.txt` | Upcoming fixtures/gameweek | `scrape_tyc.py` |
| FBref (Sports-Reference) | `src/fbref_*.csv` | Squad statistics (goals, assists, etc.) | `scrape_stats_enhanced.py` |
| FootyStats | `src/footystats_*.csv` | Advanced analytics metrics | `scrape_footystats.py` |
| Sofascore | `src/sofascore_stats.json` | Current standings, team positions | `scrape_sofascore_apify.py` |
| PDF Reports | Parsed via script | Match reports with details | `parse_reporte_pdfs.py` |
| User Glossary | `Glossary.txt` | Team name standardization mappings | Manual maintenance |

### Core Data Flow Path

```
1. LOAD DATA (pipeline.py: load_data)
   ├─ Load glossary for team normalization → load_glossary()
   ├─ Load sofascore standings → load_sofascore_data()
   ├─ Load fixtures from partidos.txt → parse_fixtures()
   └─ Load historical matches from ARG.csv → normalize team names, dates, results
   
2. BUILD FEATURES (pipeline.py: build_features)
   ├─ Calculate Elo ratings over time → calculate_all_elo_ratings()
   │  └─ Updates: K-Factor=30, Home Advantage=65 Elo points
   │  └─ Recalculated for every match chronologically
   │
   ├─ Extract Shin probabilities from odds → shin_method()
   │  └─ Converts betting odds to true probabilities
   │  └─ Handles insider trading bias
   │
   ├─ Compute trailing statistics (8-match window) → compute_trailing_features()
   │  └─ For each team at each match date:
   │     ├─ Home_Avg_GF: Average goals scored at home (last 8 matches)
   │     ├─ Home_Avg_GA: Average goals conceded at home
   │     ├─ Home_Form: Points per match (3=win, 1=draw, 0=loss)
   │     └─ Same for Away team
   │
   ├─ Calculate Poisson features → calculate_poisson_features()
   │  ├─ Expected Goals: xG_home, xG_away
   │  │   Formula: xG = (0.6×GF + 0.4×oppGA) × home_boost × elo_factor
   │  │   Clamped to [0.3, 2.5]
   │  │
   │  ├─ Outcome probabilities using Poisson distribution
   │  │   P(Home Win), P(Draw), P(Away Win)
   │  │   Calibrated for league averages (draw prob × 0.85)
   │  │
   │  └─ Expected total goals from grid summation
   │
   └─ Engineered features
      ├─ Elo_Diff = Home_Elo - Away_Elo
      ├─ Attack_Balance = Home_Avg_GF - Away_Avg_GF
      ├─ Def_Balance = Away_Avg_GA - Home_Avg_GA
      └─ Form_Balance = Home_Form - Away_Form

3. TRAIN & VALIDATE (pipeline.py: train_validate)
   ├─ Input: 24 features + target (Res: 0=Away Win, 1=Draw, 2=Home Win)
   ├─ Sample weight adjustment (Draw weight = 0.7 to reduce bias)
   ├─ TimeSeriesSplit (5 folds) → prevents data leakage
   ├─ Train CatBoost/LightGBM classifier
   ├─ Evaluate: Accuracy + Log Loss per fold
   └─ Output: trained model + CV metrics

4. PREDICT FIXTURES (pipeline.py: predict_fixtures)
   └─ For each upcoming fixture:
       ├─ Fetch latest Elo ratings from training history
       ├─ Get latest trailing stats from most recent matches
       ├─ Fetch Sofascore stats (position, points, GF/GA)
       ├─ Calculate Poisson features with new data
       ├─ Fill NaN features with training data means
       ├─ ML prediction: model.predict_proba(24 features)
       ├─ Ensemble blend: 60% ML + 40% Poisson probabilities
       ├─ Determine scoreline from:
       │   ├─ Expected goals
       │   ├─ Prediction confidence
       │   ├─ Match outcome (Home/Draw/Away)
       │   └─ Special cases (away team xG advantage, etc.)
       └─ Output: Pred_Home_Goals, Pred_Away_Goals, Prediction_Label

5. WRITE OUTPUTS (pipeline.py: write_outputs)
   ├─ Feature importance chart (PNG)
   ├─ Results text file (Resultados_YYYYMMDD.txt)
   └─ Summary statistics
```

---

## 3. Key Modules & Responsibilities

### `src/pipeline.py` - Orchestration Service
**Purpose:** Main orchestrator that coordinates entire workflow

**Key Functions:**
- `load_data()`: Loads glossary, sofascore data, historical matches, fixtures
- `build_features()`: Constructs all 24 features for ML model
- `train_validate()`: Time-series cross-validation with CatBoost/LightGBM
- `predict_fixtures()`: Generates predictions for upcoming matches
- `write_outputs()`: Saves results and feature importance chart
- `run_pipeline()`: Main entry point, orchestrates all steps

**Responsibilities:**
- Orchestrate data loading from multiple sources
- Coordinate feature engineering
- Manage model training lifecycle
- Handle error propagation

**Key Data Structures:**
```python
class PipelineResult:
    model: trained ML classifier
    elo_ratings: Dict[team_name, float]  # Final Elo for all teams
    features: List[str]  # 24 feature names
    cv_accuracies: List[float]  # CV accuracy per fold
    cv_log_losses: List[float]  # Log loss per fold
    fixtures: DataFrame  # Predictions with all columns
    output_file: str  # Path to results file
    feature_importance: DataFrame  # Feature importance ranking
```

**Feature List (24 total):**
```
Elo Features:
  - Home_Elo, Away_Elo, Elo_Diff

Trailing Stats:
  - Home_Avg_GF, Away_Avg_GF (average goals for)
  - Home_Avg_GA, Away_Avg_GA (average goals against)
  - Home_Form, Away_Form (points per match)

Engineered Balances:
  - Attack_Balance, Def_Balance, Form_Balance

Poisson Distribution:
  - xG_home, xG_away, xG_diff
  - Poisson_Home_Win, Poisson_Draw, Poisson_Away_Win
  - Expected_Home_Goals, Expected_Away_Goals, Expected_Total_Goals

Shin Method (Probability Extraction):
  - Shin_Prob_H, Shin_Prob_D, Shin_Prob_A (from betting odds)
```

---

### `src/stats_engine.py` - Mathematical Core

**Purpose:** Elo rating system and Poisson distribution calculations

**Key Functions:**

1. **Elo Rating System**
   - `expected_result(elo_team, elo_opp)`: Expected score (0-1) given Elo difference
     - Formula: 1 / (1 + 10^((opp_elo - team_elo) / 400))
   - `update_elo(home_elo, away_elo, result)`: Updates ratings after match
     - K-Factor: 30 (change per match)
     - Home Advantage: +65 Elo added to home team
     - Results: 2=Home Win, 1=Draw, 0=Away Win
   - `calculate_all_elo_ratings()`: Builds complete Elo history chronologically

2. **Expected Goals Calculation**
   - `calculate_expected_goals()`: Computes xG for both teams
     - Considers: Elo ratings, attack avg, defense avg, home boost (1.22x)
     - Formula: xG_home = (0.6×avg_gf_home + 0.4×avg_ga_away) × 1.22 × elo_factor
     - Bounds: [0.3, 2.5] goals

3. **Poisson Distribution**
   - `poisson_probability(goals, expected)`: P(exactly k goals) from scipy.stats
   - `calculate_outcome_probabilities(xG_home, xG_away)`: Derives match outcomes
     - Creates 9×9 grid of scoreline probabilities (up to 8 goals)
     - Sums: P(Home Win), P(Draw), P(Away Win)
     - Calibrates draw prob: multiply by 0.85 (league average ~33%)
     - Home advantage boost: +8% to home win prob

4. **Shin Method (Probability Extraction from Odds)**
   - `shin_method(odds)`: Converts 3-way odds to true probabilities
     - Assumes proportion z of insider traders
     - Solves equation: Σ p_i = 1 (implied probabilities)
     - Returns: calibrated probabilities + insider proportion
     - Used for Shin_Prob_H/D/A features

5. **Poisson Feature Bundle**
   - `calculate_poisson_features()`: Aggregates all Poisson-derived features
     - Returns dict with all xG, probability, and expected goals columns

**Configuration (from `src/config.py`):**
```python
BASE_ELO = 1500              # Starting Elo for new teams
K_FACTOR = 30                # Elo change per match
HOME_ADVANTAGE = 65          # Elo advantage for home team
ELO_DIVISOR = 400            # Standard Elo formula constant

BASE_GOAL_RATE = 1.89        # League average goals per match
MAX_GOALS = 8                # Upper bound for Poisson grid
HOME_BOOST = 1.22            # Home team scoring multiplier
GOAL_WEIGHT_ATTACK = 0.6     # Weight for offensive stats in xG
GOAL_WEIGHT_DEFENSE = 0.4    # Weight for defensive stats in xG
XG_MIN = 0.3                 # Minimum xG clamp
XG_MAX = 2.5                 # Maximum xG clamp

POISSON_DRAW_ADJUSTMENT = 0.85  # Calibration to league average
WIN_PROBABILITY_THRESHOLD = 0.45  # Confidence for win prediction
DRAW_PROBABILITY_THRESHOLD = 0.38
```

---

### `src/model_engine.py` - ML Prediction

**Purpose:** CatBoost/LightGBM model management and prediction generation

**Key Functions:**

1. `create_model(model_type, class_weights)`: Factory for fresh model instances
   - Supports: "catboost" (default) or "lightgbm"
   - Applies hyperparameters from config
   - Optional class weights for imbalanced data

2. `predict_gameweek()`: Core prediction logic for upcoming matches
   - **Inputs:** Fixture DataFrame, Elo ratings, trained model, historical data
   - **Process:**
     1. Fill Elo ratings for each team (fallback to BASE_ELO)
     2. Precompute latest trailing stats for all teams
     3. Load Sofascore features (position, points, GF/GA)
     4. Calculate Poisson features for each fixture
     5. Fill NaN features with training mean values
     6. ML prediction: `model.predict_proba(24 features)` → [P(Away), P(Draw), P(Home)]
     7. **Ensemble Blend:** 60% ML + 40% Poisson
        ```python
        blended[:, 0] = 0.6 * ml_away + 0.4 * poisson_away
        blended[:, 1] = 0.6 * ml_draw + 0.4 * poisson_draw
        blended[:, 2] = 0.6 * ml_home + 0.4 * poisson_home
        ```
     8. **Scoreline Determination:**
        - Base: `int(round(xG_home))` and `int(round(xG_away))`
        - Adjustment logic:
          - If away xG advantage > 0.20: Override to away win
          - If home win confidence ≥ 0.45: Ensure home > away
          - If draw confidence ≥ 0.38: Equal scorelines, xG-adjusted
          - Special logic for low/medium/high xG draw scenarios
     9. Clamp goals to [0, 6] maximum
   - **Outputs:** DataFrame with:
     - `Prediction` (0/1/2)
     - `Pred_Proba_*` (blended probabilities)
     - `Pred_Home_Goals`, `Pred_Away_Goals`
     - `Prediction_Label` ("Home Win" / "Draw" / "Away Win")

**Hyperparameters (`src/config.py`):**
```python
# CatBoost (default)
{
    "iterations": 500,
    "learning_rate": 0.04,
    "depth": 6,
    "l2_leaf_reg": 3,
    "bootstrap_type": "Bernoulli",
    "subsample": 0.8,
    "colsample_bylevel": 0.8,
    "random_state": 42,
}

# LightGBM
{
    "n_estimators": 500,
    "learning_rate": 0.04,
    "num_leaves": 32,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}
```

---

### `src/features.py` - Feature Engineering

**Purpose:** Trailing statistics computation for recent team form

**Key Functions:**

1. `get_team_trailing_stats(history, window)`: Computes stats from match history
   - **Input:** List of dicts with {gf, ga, is_home}
   - **Calculates:**
     - `avg_gf`: Average goals scored
     - `avg_ga`: Average goals conceded
     - `avg_gd`: Goal difference average
     - `form`: Points per match (3 for win, 1 for draw, 0 for loss)
     - `matches`: Count of matches in window
   - **Window**: Limits to last N matches (default: 8)

2. `compute_trailing_features(matches_df, window=8)`: Builds features for training
   - **Process:** Chronological pass through match history
     - For each match date, calculate trailing stats at that point in time
     - Prevents data leakage (stats only from matches before current date)
   - **Output columns:**
     ```
     Home_Avg_GF, Home_Avg_GA, Home_Avg_GD, Home_Form, Home_Matches
     Away_Avg_GF, Away_Avg_GA, Away_Avg_GD, Away_Form, Away_Matches
     ```

3. `get_all_teams_latest_stats(matches_df, window=8)`: Latest stats for prediction
   - **Use case:** During prediction phase, get most recent 8-match average for each team
   - **Returns:** Dict[team_name, {avg_gf, avg_ga, avg_gd, form, matches}]

---

### `src/data_processing.py` - Data Loading & Normalization

**Purpose:** Load and standardize all input data sources

**Key Functions:**

1. `load_glossary(filepath)`: Team name mapping dictionary
   - **File format:** `ORIGINAL_NAME -> CANONICAL_NAME` (delimiter: ->, =, or :)
   - **Purpose:** Standardize team names across different data sources
   - **Example:** "Boca Juniors" → "BOCA JUNIORS"

2. `normalize_team_name(name, glossary)`: Standardizes single team name
   - **Steps:**
     1. Strip whitespace, convert to uppercase
     2. Apply glossary mapping (if exists)
     3. Remove punctuation (dots, dashes)
     4. Remove accents (Á→A, Ñ→N, etc.)
     5. Remove extra whitespace

3. `load_sofascore_data(filepath, glossary)`: Loads standings from JSON
   - **Expected JSON structure:** `{teams: [{name, position, points, goals_for, goals_against}, ...]}`
   - **Returns:** Dict[TEAM_UPPER, {position, points, goals_for, goals_against}]

4. `clean_partidos_file(fixtures_path, glossary)`: Normalizes fixture file
   - **Input format:** Typically "TEAM1 - TEAM2" per line
   - **Applies:** Team name normalization to standardize

5. `parse_fixtures(fixtures_path, glossary)`: Parses upcoming matches
   - **Returns:** DataFrame with {Home, Away, ...} columns
   - **Handles:** Empty file gracefully

6. `load_data()` (wrapper): Coordinates loading all sources
   - Returns: (glossary, sofascore_data, historical_matches, upcoming_fixtures)

---

### `src/utils.py` - Logging & Utilities

**Purpose:** Simple logging and file utilities

**Functions:**
- `log_info(message)`: Print [INFO] prefix
- `log_ok(message)`: Print [OK] prefix
- `log_error(message)`: Print [ERROR] prefix
- `log_warning(message)`: Print [WARNING] prefix
- `find_latest_file(pattern)`: Glob pattern to get most recently modified file

---

### `main.py` - Entry Point

**Purpose:** Simple orchestration wrapper

**Flow:**
1. Call `run_pipeline()` from `src/pipeline.py`
2. Extract results (model, elo_ratings, features)
3. Print summary statistics (CV accuracy, feature count)
4. Log output file path

---

## 4. Data Scrapers (Collection Layer)

### Scraper Files

| File | Source | Output | Method | Frequency |
|------|--------|--------|--------|-----------|
| `scrape_tyc.py` | TyC Sports | `partidos.txt` | BeautifulSoup | Weekly |
| `scrape_stats_enhanced.py` | FBref (Sports-Reference) | `src/fbref_*.csv` | Selenium | Weekly |
| `scrape_stats_manual.py` | FBref/Footystats | `src/results*.csv` | Chrome DevTools Protocol | On-demand |
| `scrape_footystats.py` | Footystats | `src/footystats_*.csv` | Playwright | Weekly |
| `scrape_sofascore_apify.py` | Sofascore (via Apify) | `src/sofascore_stats.json` | Apify API client | Weekly |
| `parse_reporte_pdfs.py` | PDF reports | Parsed to `data/ARG.csv` | pdfplumber | As needed |
| `update_arg_csv.py` | Football-Data.co.uk | `data/ARG.csv` | Manual/HTTP | Weekly |

### Data Collection Architecture

```
Weekly Workflow:
1. scrape_tyc.py → Extract upcoming fixtures from TyC Sports
2. scrape_stats_enhanced.py → Get latest FBref squad stats
3. scrape_sofascore_apify.py → Fetch current standings from Sofascore
4. main.py → Run pipeline with collected data

Outputs → Results written to:
- Resultados_YYYYMMDD.txt (human-readable predictions)
- feature_importance_YYYYMMDD.png (chart)
```

---

## 5. Configuration System

### `src/config.py` - Single Source of Truth

All hyperparameters centralized in one file. Categories:

**1. Elo Parameters**
```python
BASE_ELO = 1500              # Starting rating
K_FACTOR = 30                # Change per match
HOME_ADVANTAGE = 65          # Home team bonus
ELO_DIVISOR = 400            # Standard Elo constant
ELO_FACTOR_DENOM = 5000      # Elo scaling factor
```

**2. Poisson Parameters**
```python
BASE_GOAL_RATE = 1.89        # Liga Profesional average
MAX_GOALS = 8                # Grid size
HOME_BOOST = 1.22            # Home scoring multiplier
GOAL_WEIGHT_ATTACK = 0.6     # Attack stat weight
GOAL_WEIGHT_DEFENSE = 0.4    # Defense stat weight
XG_MIN, XG_MAX = 0.3, 2.5    # xG bounds
```

**3. Probability Calibration**
```python
POISSON_DRAW_ADJUSTMENT = 0.85  # Reduce draw bias
WIN_PROBABILITY_THRESHOLD = 0.45
DRAW_PROBABILITY_THRESHOLD = 0.38
```

**4. Model Selection**
```python
MODEL_TYPE = os.environ.get("ML_PREDICTOR_MODEL", "catboost")
# Set via environment variable, defaults to CatBoost
```

**5. Feature Engineering**
```python
TRAILING_WINDOW = 8          # Last N matches for stats
```

**6. Result Encoding**
```python
RESULT_ENCODING = {"H": 2, "D": 1, "A": 0}
RESULT_DECODING = {2: "Home Win", 1: "Draw", 0: "Away Win"}
```

### Environment Variables

- `ML_PREDICTOR_MODEL`: Set to "lightgbm" or "catboost" (default: catboost)

### Data Files

**Input Files (Required):**
- `data/ARG.csv`: Historical match data with columns: Date, Home, Away, Res (H/D/A), HG, AG, odds (B365CH, B365CD, B365CA)
- `partidos.txt`: Upcoming fixtures, format: "TEAM1 - TEAM2"
- `Glossary.txt`: Team name mappings (optional but recommended)

**Generated Files (During Pipeline):**
- `src/sofascore_stats.json`: Current standings (auto-loaded by pipeline)
- `src/fbref_*.csv`: Squad statistics (consumed by feature engineering)
- `src/footystats_*.csv`: Advanced metrics (referenced but not actively used)

**Output Files (After Pipeline):**
- `Resultados_YYYYMMDD.txt`: Human-readable predictions
- `feature_importance_YYYYMMDD.png`: Feature importance bar chart

---

## 6. Dependencies & Integrations

### Python Package Dependencies

**Core Data Science:**
```
pandas>=2.0.0          # Data manipulation
numpy>=1.24.0          # Numerical computing
scipy>=1.11.0          # Scientific functions (Poisson distributions)
```

**Machine Learning:**
```
catboost>=1.2.0        # Gradient boosting classifier (default)
lightgbm>=4.0.0        # Alternative gradient boosting
scikit-learn>=1.3.0    # CV splits, metrics
```

**Web Scraping:**
```
requests>=2.31.0       # HTTP requests
beautifulsoup4>=4.12.0 # HTML parsing
lxml>=4.9.0            # XML/HTML backend
playwright>=1.40.0     # Browser automation (Footystats)
selenium>=4.15.0       # Browser automation (FBref)
webdriver-manager      # Chromedriver management
fake-useragent>=1.4.0  # User agent randomization
```

**External APIs:**
```
apify-client>=1.0.0    # Sofascore data via Apify
```

**Document Processing:**
```
pdfplumber>=0.10.0     # PDF parsing for reports
```

**Testing:**
```
pytest>=7.4.0          # Unit testing framework
```

### External Service Integrations

1. **Football-Data.co.uk**
   - Provides: `ARG.csv` historical match data with odds
   - Manual download: https://www.football-data.co.uk/argentina.php
   - Integration: Manual file replacement in `data/ARG.csv`

2. **TyC Sports** (Argentine broadcaster)
   - Provides: Upcoming fixture dates and teams
   - Integration: `scrape_tyc.py` (BeautifulSoup)
   - Output: `partidos.txt`

3. **FBref/Sports-Reference**
   - Provides: Squad statistics (goals, assists, etc.)
   - Integration: `scrape_stats_enhanced.py` (Selenium) or manual (CDP)
   - Output: `src/fbref_*.csv` files

4. **FootyStats**
   - Provides: Advanced metrics and analytics
   - Integration: `scrape_footystats.py` (Playwright)
   - Output: `src/footystats_*.csv` files

5. **Sofascore** (via Apify)
   - Provides: Current standings, points, team positions
   - Integration: `scrape_sofascore_apify.py` (API client)
   - Requires: Apify API key (in environment)
   - Output: `src/sofascore_stats.json`

---

## 7. Entry Points

### Primary Entry Point: `main.py`

**Execution:**
```bash
python main.py
```

**Flow:**
1. Calls `run_pipeline()` from `src/pipeline.py`
2. Returns: (model, elo_ratings, features)
3. Prints summary to console

**Output:**
- Console: CV accuracy, feature count, fixtures predicted, output file path
- Files: `Resultados_YYYYMMDD.txt`, `feature_importance_YYYYMMDD.png`

### Alternative Entry Points

**Via PowerShell Menu:**
```powershell
.\run_model.ps1
```
Interactive menu with options:
1. Parse Reporte PDFs → `parse_reporte_pdfs.py`
2. Scrape FBref Stats → `scrape_stats_enhanced.py`
3. Scrape Sofascore → `scrape_sofascore_apify.py`
4. Scrape TyC Sports → `scrape_tyc.py`
5. Run Main Prediction → `python main.py`
6. Run All (Data + Prediction)

**API Server (Development):**
```bash
python scripts/api_server.py --port 8000
```
REST endpoints:
- `GET /predictions` - Latest predictions
- `GET /teams` - Available teams
- `GET /stats` - Historical statistics
- `GET /health` - Health check

---

## 8. File Structure & Organization

### Directory Tree

```
ML_Predictor2026_V2/
│
├── main.py                          # Entry point - orchestrates pipeline
├── requirements.txt                 # Python dependencies
├── Glossary.txt                     # Team name normalization mappings
├── partidos.txt                     # Upcoming fixtures
├── Readme.md                        # Documentation
├── run_model.ps1                    # PowerShell menu wrapper
│
├── data/
│   └── ARG.csv                      # Historical match data (2000+ matches)
│
├── src/                             # Core source code
│   ├── __init__.py
│   ├── config.py                    # Centralized configuration & hyperparameters
│   ├── pipeline.py                  # Orchestration service (load → feature → train → predict)
│   ├── model_engine.py              # ML model creation & prediction logic
│   ├── stats_engine.py              # Elo ratings & Poisson distributions
│   ├── features.py                  # Trailing feature engineering
│   ├── data_processing.py           # Data loading & normalization
│   ├── utils.py                     # Logging & utility functions
│   │
│   └── Generated CSV Files (outputs from scrapers)
│       ├── fbref_league_table_*.csv       # Squad stats from FBref
│       ├── fbref_stats_advanced_*.csv     # Advanced stats from FBref
│       ├── fbref_other_*.csv              # Other metrics from FBref
│       ├── footystats_league_*.csv        # Footystats metrics
│       ├── footystats_stats_advanced_*.csv
│       ├── footystats_other_*.csv
│       └── sofascore_stats.json           # Current standings (JSON)
│
├── scripts/                         # Utility scripts & scrapers
│   ├── api_server.py                # REST API server (development)
│   ├── api_predict.py               # Prediction API handler
│
├── scrapers/ (at root level - Python files)
│   ├── scrape_tyc.py                # TyC Sports fixtures → partidos.txt
│   ├── scrape_stats_enhanced.py     # FBref via Selenium → fbref_*.csv
│   ├── scrape_stats_manual.py       # FBref/Footystats via CDP (manual)
│   ├── scrape_footystats.py         # Footystats via Playwright → footystats_*.csv
│   ├── scrape_sofascore_apify.py    # Sofascore via Apify → sofascore_stats.json
│   ├── parse_reporte_pdfs.py        # PDF reports → data/ARG.csv updates
│   └── update_arg_csv.py            # Manual downloader for ARG.csv
│
├── tests/                           # Test suite
│   └── test_main.py                 # Unit tests for core functions
│
├── Reporte/                         # PDF reports (source data)
│
├── DEV_CONTEXT/                     # Development documentation
│   ├── CODEBASE_MAP.md              # This file
│   └── (other dev docs)
│
├── .planning/                       # Planning & roadmap
│
├── .venv/                           # Python virtual environment
│
└── Output Files (Generated after pipeline run)
    ├── Resultados_YYYYMMDD.txt      # Predictions in text format
    ├── feature_importance_*.png     # Feature importance chart
    └── Resultados_Simple_*.txt      # Simplified predictions
```

### Naming Conventions

**Python Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `data_processing.py`)
- Classes: `PascalCase` (e.g., `PipelineResult`)
- Functions: `snake_case` (e.g., `calculate_poisson_features()`)
- Constants: `UPPER_CASE` (e.g., `BASE_ELO`, `HOME_ADVANTAGE`)

**CSV Files:**
- Format: `{source}_{type}_{date}_{matchweek}.csv`
- Examples:
  - `fbref_league_table_20260307_10.csv`
  - `footystats_stats_advanced_20260314_1.csv`

**JSON Files:**
- `sofascore_stats.json` - Standings snapshot

**Output Files:**
- Results: `Resultados_{YYYYMMDD}.txt`
- Charts: `feature_importance_{YYYYMMDD}.png`

---

## 9. Key Algorithms & Mathematical Foundations

### 1. Elo Rating System

**Purpose:** Dynamic measure of team strength

**Formula:**
```
E_team = 1 / (1 + 10^((E_opp - E_team) / 400))

New_Elo = Old_Elo + K * (Result - Expected)
```

**Parameters:**
- K-Factor: 30 (higher = more responsive)
- Home Advantage: +65 Elo (applied before calculation)
- Starting Elo: 1500 (new teams)

**Properties:**
- Self-normalizing (maintains total Elo across all teams)
- Reflects long-term strength
- Accounts for home advantage

---

### 2. Expected Goals (xG) Calculation

**Purpose:** Quantify attacking/defensive quality

**Formula:**
```
xG_home = (0.6 × avg_gf_home + 0.4 × avg_ga_away) × 1.22 × elo_factor

where elo_factor = 1 + (elo_diff / 5000)

Bounds: [0.3, 2.5]
```

**Components:**
- **Attack Term (0.6 weight):** Team's offensive capability
- **Defense Term (0.4 weight):** Opponent's vulnerability
- **Home Boost (1.22x):** Home teams score more
- **Elo Factor:** Superior teams boost xG, inferior reduce it
- **Clamping:** Prevents extreme values (unrealistic scores)

---

### 3. Poisson Goal Modeling

**Purpose:** Realistic probability distribution for goal scoring

**Formula:**
```
P(X = k goals) = (λ^k * e^-λ) / k!

where λ = expected goals (xG)
```

**Application:**
1. Generate xG_home and xG_away
2. Create 9×9 grid: grid[h,a] = P(h goals) × P(a goals)
3. Normalize grid: grid / sum(grid)
4. Sum outcomes:
   - Home Win: sum of grid[h>a]
   - Draw: sum of grid[h==a]
   - Away Win: sum of grid[h<a]

**Calibration:**
- Draw prob multiplied by 0.85 (league average ~33%, raw Poisson ~25%)
- Home advantage boost: +8% to home win prob
- Re-normalize to probabilities sum to 1.0

---

### 4. Shin Method (Probability Extraction)

**Purpose:** Extract true probabilities from betting odds

**Assumption:** Proportion z of insider traders exploit market inefficiency

**Formula:**
```
π_i = 1/odds_i  (implied probability)

p_i = ((√(z² + 4(1-z)π_i) - z) / (2(1-z)))²

Solve: Σp_i = 1 for optimal z ∈ [0, 1)
```

**Output:**
- p_h, p_d, p_a: True probabilities (Shin-corrected)
- z_optimal: Estimated insider trader proportion
- Used as Shin_Prob_H/D/A features in ML model

---

### 5. Ensemble Prediction (ML + Poisson)

**Purpose:** Combine ML accuracy with Poisson's interpretability

**Formula:**
```
Blended_Prob = 0.6 × ML_Prob + 0.4 × Poisson_Prob

Final_Prediction = argmax(Blended_Prob)
```

**Rationale:**
- ML captures complex patterns but may overfit
- Poisson is mathematically grounded but ignores context
- Blend leverages both: ML for nuance, Poisson for calibration

**Benefits:**
- Reduces draw prediction bias
- More stable when data is limited
- Interpretable by stakeholders

---

## 10. Testing Strategy

### Test File: `tests/test_main.py`

**Coverage Areas:**

**1. Team Name Normalization (3 tests)**
- Basic uppercase conversion
- Glossary mapping
- Special character handling

**2. Elo Calculations (5 tests)**
- Expected result calculation
- Home win update
- Away win update
- Draw update
- Home advantage application

**3. Poisson Distribution (7 tests)**
- Probability sum normalization
- Peak probability matching
- xG calculation bounds
- Outcome probability sum
- Strong home team advantage
- Draw probability ranges
- Expected goals accuracy

**4. Trailing Features (4 tests)**
- Empty history handling
- Single match stats
- Form calculation
- Window limiting

**5. Integration Tests (2 tests)**
- Full Poisson workflow
- Elo + Poisson integration

**Run Tests:**
```bash
pytest tests/test_main.py -v
```

**Coverage:**
- 21 test cases covering core functions
- Tests deterministic calculations (reproducible)
- No mocking of external services
- All tests pass with current codebase

---

## 11. Known Configuration Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `BASE_ELO` | 1500 | Starting Elo rating |
| `K_FACTOR` | 30 | Elo volatility per match |
| `HOME_ADVANTAGE` | 65 | Elo bonus for home team |
| `BASE_GOAL_RATE` | 1.89 | Liga Profesional avg goals/match |
| `HOME_BOOST` | 1.22 | xG multiplier for home team |
| `TRAILING_WINDOW` | 8 | Matches for form calculation |
| `MAX_GOALS` | 8 | Poisson grid upper bound |
| `XG_MIN` | 0.3 | Minimum expected goals |
| `XG_MAX` | 2.5 | Maximum expected goals |
| `POISSON_DRAW_ADJUSTMENT` | 0.85 | Draw prob calibration |
| `GOAL_WEIGHT_ATTACK` | 0.6 | xG attack stat weight |
| `GOAL_WEIGHT_DEFENSE` | 0.4 | xG defense stat weight |
| `RESULT_ENCODING` | {H:2, D:1, A:0} | ML target encoding |

---

## 12. Data Quality & Validation

### Input Validation Points

1. **Historical Data (ARG.csv)**
   - Required columns: Date, Home, Away, Res, HG, AG
   - NaN handling: Drop rows with missing key columns
   - Date parsing: dayfirst=True (Latin American format)
   - Result normalization: Convert H/D/A to 2/1/0

2. **Fixtures File (partidos.txt)**
   - Format: "TEAM1 - TEAM2" (one per line)
   - Team name normalization applied
   - Graceful handling if file missing

3. **Team Name Glossary**
   - Optional (system works without)
   - Multiple delimiter support (→, =, :)
   - Comments supported (lines starting with #)

4. **Sofascore Data**
   - Expected JSON structure: `{teams: [...]}`
   - Fallback values: position=28, points=0 if missing
   - Upper-casing for key lookup

### Missing Data Handling

| Field | Handling |
|-------|----------|
| Trailing stats | Fill with training data mean |
| Sofascore standings | Use defaults (28th place, 0 points) |
| Betting odds | Skip Shin calculation, use NaN |
| Historical results | Drop rows with missing data |
| Elo ratings | Initialize new teams at 1500 |

---

## 13. Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Elo calculation | O(n) | Single pass through history |
| Trailing features | O(n × m) | n matches, m teams (manageable ~2000 matches) |
| Poisson features | O(n) | Per-match calculation |
| ML training | O(n × f²) | n samples, f=24 features, tree depth=6 |
| Prediction | O(k × f) | k fixtures, f features |

### Space Complexity

| Data Structure | Size | Notes |
|---|---|---|
| Historical matches | ~2000 rows × 40 cols | ARG.csv (5-25 years data) |
| Feature matrix | 2000 × 24 | Training data |
| Elo history | ~2000 rows × 4 cols | (Date, Home, Away, Elo) |
| Trained model | ~50 MB | CatBoost model object |

### Runtime

- **Pipeline execution:** ~5-10 seconds (typical)
  - Data loading: 1s
  - Feature engineering: 2s
  - Model training (5-fold CV): 5s
  - Prediction: <1s
- **Prediction latency:** <100ms per match

---

## 14. Error Handling & Logging

### Logging Strategy

All logging via `src/utils.py`:
- `log_info()` → [INFO] prefix
- `log_ok()` → [OK] prefix (success)
- `log_error()` → [ERROR] prefix (failure)
- `log_warning()` → [WARNING] prefix (caution)

### Exception Handling

**In `pipeline.py`:**
```python
try:
    # Pipeline execution
except Exception as e:
    log_error(f"Pipeline failed: {e}")
    raise  # Re-raise for caller to handle
```

**In scrapers:**
- Graceful degradation if data source unavailable
- Warning logged, pipeline continues with fallback

### Common Error Scenarios

| Error | Cause | Resolution |
|-------|-------|-----------|
| "No files match pattern" | Scraper not run | Run scraper first |
| "Fixtures file not found" | Missed scrape_tyc.py | Run scrape_tyc.py |
| "Glossary not found" | Manual file deleted | Recreate or continue without |
| "CSV parse error" | Corrupted ARG.csv | Redownload or restore backup |

---

## 15. Development Guidelines

### Adding New Features

**To add a new feature for ML model:**

1. **Define calculation** in `src/stats_engine.py` or `src/features.py`
2. **Add to feature list** in `src/pipeline.py` (FEATURE_COLUMNS)
3. **Compute in build_features()** with `calculate_*` function
4. **Test** with `tests/test_main.py`
5. **Document** in this map

**Example: Add a new feature**
```python
# In src/features.py or stats_engine.py
def calculate_new_feature(param1, param2):
    """New feature calculation."""
    return value

# In src/pipeline.py - build_features()
new_features = [calculate_new_feature(...) for _, r in matches.iterrows()]
matches = pd.concat([matches, pd.DataFrame(new_features, index=matches.index)], axis=1)

# In src/pipeline.py - FEATURE_COLUMNS
FEATURE_COLUMNS = [
    # ... existing features ...
    "New_Feature_Name",  # Add here
]
```

### Modifying Configuration

1. Edit `src/config.py` constants only
2. Never hardcode values in functions
3. Document rationale for parameter changes
4. Run full test suite after changes

---

## 16. Future Enhancement Opportunities

### Potential Improvements

1. **Sequence Modeling**
   - LSTM for temporal patterns
   - Recurrent features for form sequences

2. **Advanced Poisson**
   - Conway-Maxwell-Poisson (accounts for over-dispersion)
   - Hurdle models (0-inflation for draws)

3. **External Data Integration**
   - Weather data (affects playing style)
   - Injury data (affects squad strength)
   - Transfer market values (player quality)

4. **Market-Driven Features**
   - Betting odds as direct features
   - Sharpe ratio of odds
   - Market movement over time

5. **Ensemble Methods**
   - Stacking (3-level model)
   - Multi-model voting (ensemble of ensembles)

6. **API Expansion**
   - Real-time prediction API
   - Historical performance tracking
   - Confidence intervals

---

## Summary

**This codebase implements a sophisticated football prediction system combining:**

- ✅ **Dynamic Elo ratings** for team strength tracking
- ✅ **Poisson distribution** for realistic goal modeling
- ✅ **Gradient boosting** (CatBoost/LightGBM) for pattern recognition
- ✅ **Ensemble prediction** (60% ML + 40% Poisson)
- ✅ **Time-series cross-validation** to prevent data leakage
- ✅ **Multiple data sources** (FBref, Sofascore, TyC Sports, Apify)
- ✅ **Comprehensive feature engineering** (24 features total)
- ✅ **Probabilistic calibration** (Shin method from odds)

**Key Strengths:**
- Interpretable components (Poisson is mathematically sound)
- Prevents overfitting (time-series CV, sample weights)
- Handles imbalanced classes (draw weight = 0.7)
- Extensible architecture (easy to add features/sources)
- Production-ready (error handling, logging, tests)

**Main Pipeline Flow:**
```
Raw Data → Normalize → Compute Features (Elo + Poisson + Stats) 
→ Train ML Model (5-fold CV) → Blend with Poisson 
→ Predict Outcomes + Scorelines → Output Results
```

