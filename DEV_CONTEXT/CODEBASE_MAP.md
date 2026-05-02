# CODEBASE_MAP.md

**Last Updated:** 2026-05-02

## Pipeline Flow

```
load_data()
  ├─ load_glossary()              → team name mappings
  ├─ load_sofascore_data()        → current standings
  ├─ parse_fixtures()             → Partidos.txt → DataFrame
  ├─ pd.read_csv(ARG.csv)         → historical matches
  ├─ apply_header_mapping()       → canonical column names
  └─ validate_pipeline_inputs()   → pre-flight checks + [SEASON CHECK]

build_features()
  ├─ shin_method()                → Shin_Prob_H/D/A from betting odds
  ├─ calculate_all_elo_ratings()  → Home_Elo, Away_Elo per match
  ├─ compute_trailing_features()  → exponential-decay 8-match window
  ├─ calculate_expected_goals()   → xG_home, xG_away (vectorized)
  ├─ calculate_outcome_probabilities() → Poisson_Home_Win/Draw/Away_Win
  └─ engineered balances          → Elo_Diff, Attack_Balance, Def_Balance, Form_Balance

train_validate()
  ├─ validate_model_features()    → check NaN/Inf/bounds
  ├─ TimeSeriesSplit(5 folds)     → no data leakage
  ├─ CatBoost/LightGBM.fit()      → sample_weight: draws=0.7
  └─ baseline comparison          → naive_ll=1.077, bookie_ll from odds

predict_fixtures()
  └─ predict_gameweek()
      ├─ get_all_teams_latest_stats()  → trailing stats (Home_GF/Away_GF fallback)
      ├─ calculate_poisson_features()  → per-fixture xG + probabilities
      ├─ model.predict_proba()         → ML probabilities
      ├─ ensemble blend               → 60% ML + 40% Poisson
      └─ _calculate_hybrid_goals()    → floor(xG) + ML directional adjustment

write_outputs()
  ├─ PrediccionFechaXX.txt        → scorelines + metrics comparison
  └─ feature_importance_*.png     → bar chart
```

## Feature List (24 total)

```
Elo:        Home_Elo, Away_Elo, Elo_Diff
Trailing:   Home_Avg_GF, Away_Avg_GF, Home_Avg_GA, Away_Avg_GA, Home_Form, Away_Form
Balances:   Attack_Balance, Def_Balance, Form_Balance
Poisson:    xG_home, xG_away, xG_diff,
            Poisson_Home_Win, Poisson_Draw, Poisson_Away_Win,
            Expected_Home_Goals, Expected_Away_Goals, Expected_Total_Goals
Shin:       Shin_Prob_H, Shin_Prob_D, Shin_Prob_A
```

## Key Algorithms

### Elo
```
E = 1 / (1 + 10^((opp_elo - team_elo) / 400))
new_elo = old_elo + 30 * (result - E)
Home gets +65 Elo before calculation. Bounds: [800, 2800].
```

### xG
```
xG_home = (0.55 * avg_gf_home + 0.45 * avg_ga_away) * 1.15 * elo_factor
xG_away = (0.55 * avg_gf_away + 0.45 * avg_ga_home) / elo_factor
elo_factor = 1 + (elo_diff / 5000)
Bounds: [0.3, 2.5]
NaN fallback: BASE_GOAL_RATE = 2.22 (used for new/promoted teams only)
```

### Poisson Outcome Probabilities
```
grid[h,a] = P(home=h) * P(away=a)   (9x9 grid)
p_draw *= 0.85                        (reduce raw Poisson draw bias)
p_home_win += 0.08                    (home advantage boost)
re-normalize to sum=1.0
```

### Scoreline (_calculate_hybrid_goals)
```
base: m_h = floor(xG_home), m_a = floor(xG_away)
if max(p_h, p_d, p_a) >= 0.35:
  home win predicted → ensure m_h > m_a; bump if p_h >= 0.50
  away win predicted → symmetric
  draw predicted     → m_h = m_a = max(m_h, m_a)
clamp to [0, MAX_PREDICTED_GOALS=6]
```

### Ensemble
```
blended = 0.6 * ML_proba + 0.4 * Poisson_proba
prediction = argmax(blended)
```

## Module Reference

### src/stats_engine.py
- `expected_result(elo_team, elo_opp)` → float
- `update_elo(home_elo, away_elo, result)` → (new_home, new_away)
- `calculate_all_elo_ratings(matches_df, base_elo)` → (ratings_dict, history_list)
- `calculate_expected_goals(elo_h, elo_a, avg_gf_h, avg_gf_a, avg_ga_h, avg_ga_a)` → (xG_h, xG_a)
- `calculate_outcome_probabilities(xG_home, xG_away)` → dict
- `calculate_poisson_features(...)` → dict
- `shin_method(odds)` → (true_probs, z_optimal)
- `calibrate_poisson_params(matches_df)` → calibration report dict

### src/features.py
- `get_team_trailing_stats(history, window)` → dict
- `compute_trailing_features(matches_df, window=8)` → DataFrame (exponential decay)
- `get_all_teams_latest_stats(matches_df, window=8)` → dict — reads `GF`/`GA` with `Home_GF`/`Away_GF` fallback
- `get_team_stats_from_history(matches_df, team_name, window=8)` → dict (legacy)

### src/model_engine.py
- `create_model(model_type, class_weights)` → CatBoost or LightGBM instance
- `_calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)` → (home_goals, away_goals)
- `predict_gameweek(fixtures_df, elo_ratings, model, features, df_mean, historical_matches, sofascore_data)` → DataFrame

### src/data_processing.py
- `normalize_team_name(name, glossary)` → str
- `load_glossary(filepath)` → dict
- `apply_header_mapping(df, provider)` → (df, log)
- `load_sofascore_data(filepath, glossary)` → dict
- `parse_fixtures(filepath, glossary)` → (DataFrame, header_line, summary_dict)
- `clean_partidos_file(path, glossary)` → None

### src/validation.py
- `validate_pipeline_inputs(glossary, matches, fixtures, sofascore)` → (bool, errors)
- `validate_model_features(X, features)` → ValidationResult

### src/scraper_utils.py
- `@resilient_scraper(max_retries, backoff_factor, timeout)` → decorator
- `detect_captcha_in_content(content)` → bool
- `get_health_monitor()` → ScraperHealthMonitor

## Data Files

| File | Format | Notes |
|------|--------|-------|
| `data/ARG.csv` | CSV | football-data.co.uk format; auto-updated on pipeline start |
| `Partidos.txt` | Text | `FECHA N - dates\nTeam - Team:\n...` |
| `Glossary.txt` | Text | `Source Name -> CANONICAL NAME` |
| `src/sofascore_stats.json` | JSON | Apify or manual format; both supported |
| `src/fbref_*.csv` | CSV | Squad stats from FBref scraper |
| `src/footystats_*.csv` | CSV | Advanced metrics from FootyStats scraper |

## Configuration Constants (src/config.py)

| Constant | Value | Purpose |
|----------|-------|---------|
| BASE_ELO | 1500 | Starting Elo for new teams |
| K_FACTOR | 30 | Elo change per match |
| HOME_ADVANTAGE | 65 | Elo bonus for home team |
| BASE_GOAL_RATE | 2.22 | NaN fallback for new teams in xG calc |
| HOME_BOOST | 1.15 | xG multiplier for home team |
| GOAL_WEIGHT_ATTACK | 0.55 | Attack stat weight in xG |
| GOAL_WEIGHT_DEFENSE | 0.45 | Defense stat weight in xG |
| XG_MIN / XG_MAX | 0.3 / 2.5 | xG clamp bounds |
| POISSON_DRAW_ADJUSTMENT | 0.85 | Reduce raw Poisson draw probability |
| HOME_ADVANTAGE_BOOST | 0.08 | +8% to home win probability |
| ML_POISSON_BLEND_RATIO | 0.6 | 60% ML, 40% Poisson |
| TRAILING_WINDOW | 8 | Matches for form calculation |
| RESULT_ENCODING | H=2, D=1, A=0 | ML target encoding |

## Test Suite (tests/)

| File | Tests | Coverage |
|------|-------|---------|
| `test_main.py` | 29 | Normalization, Elo, Poisson, trailing features, integration, bug regression |
| `test_scraper_utils.py` | 15 | CAPTCHA detection, retry decorator, output validation, health monitor |
| New tests (May 2026) | 5 | `parse_fixtures`, ensemble blending, new-team detection, GF/GA mapping, trailing features column names |

Run: `python -m pytest tests/ -v` — expect 34+ passing.
