# SYSTEM_KNOWLEDGE.md

## Technical Details

### Poisson Distribution Implementation

**BASE_GOAL_RATE = 1.89**: Calibrated for Liga Profesional Argentina (~1.89 avg goals/match)

**xG Calculation Formula**:
```
xG_home = BASE_GOAL_RATE * home_advantage * attack_factor * defense_factor
xG_away = BASE_GOAL_RATE * attack_factor * defense_factor
```

**Attack/Defense Factors**:
- Derived from trailing 8-match averages
- Normalized against league average
- Clamped to 0.3-2.5 range to prevent extreme values

**Poisson Probability**:
```
P(goals = k) = (xG^k * e^(-xG)) / k!
```

**Outcome Probabilities**:
- Home Win: sum of P(home_goals > away_goals)
- Draw: sum of P(home_goals = away_goals)
- Away Win: sum of P(home_goals < away_goals)

### Apify Integration

**API Token**: set via `APIFY_API_TOKEN` environment variable (do not commit)

**Actor**: azzouzana/sofascore-scraper-pro

**Target URL**:
https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155#tab:standings

**Dataset Storage**: Results saved to src/sofascore_stats.json

### File Formats

#### sofascore_stats.json - Apify Format
```json
{
  "teams": [{
    "standings": [{
      "rows": [{
        "team": {"name": "Team Name"},
        "points": 15,
        "matches": 7,
        "wins": 4,
        "draws": 3,
        "losses": 0,
        "goalsFor": 7,
        "goalsAgainst": 2,
        "goalDifference": 5
      }]
    }]
  }]
}
```

#### sofascore_stats.json - Manual Format
```json
{
  "teams": [{
    "normalized": "ESTUDIANTES LP",
    "position": 1,
    "points": 15,
    "played": 7,
    "won": 4,
    "drawn": 3,
    "lost": 0,
    "goals_for": 7,
    "goals_against": 2,
    "goal_difference": 5
  }]
}
```

### Key Functions & Modules

#### src/stats_engine.py
- `expected_result()` / `update_elo()`: Dynamic Elo rating management.
- `calculate_expected_goals()`: Computes xG from Elo and trailing stats.
- `calculate_outcome_probabilities()`: Derives H/D/A probabilities from Poisson distributions.
- `calculate_poisson_features()`: Orchestrates all Poisson-derived feature generation.

#### src/data_processing.py
- `load_sofascore_data()`: Loads and parses Sofascore JSON (supports Apify and Manual formats).
- `load_glossary()`: Loads team name mappings.
- `normalize_team_name()` / `replace_spanish_vowel_accents()`: Text normalization.
- `clean_partidos_file()` / `parse_fixtures()`: Fixture data ingestion.

#### src/features.py
- `compute_trailing_features()`: High-level feature generation for historical data.
- `get_team_trailing_stats()`: Lower-level stat computation from a team's history.
- `get_team_stats_from_history()`: Retrieves stats for specific teams at prediction time.

#### src/model_engine.py
- `create_model()`: Factory for LightGBM or CatBoost models.
- `predict_gameweek()`: Main prediction loop using ML model and Poisson adjustment.

#### main.py (Orchestration)
- High-level script that imports from `src/` modules to run the full pipeline.

### Configuration

**Elo Parameters**:
- BASE_ELO = 1500
- K_FACTOR = 30
- HOME_ADVANTAGE = 65

**Model Parameters**:
- Trailing window: 8 matches
- Max goals in Poisson: 6
- Base goal rate: 1.89

### Dependencies

Core: pandas, numpy, scipy, lightgbm, catboost, scikit-learn
Scraping: requests, beautifulsoup4, lxml, playwright, selenium
API: apify-client
PDF: pdfplumber
Testing: pytest
