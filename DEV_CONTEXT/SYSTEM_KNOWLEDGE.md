# SYSTEM_KNOWLEDGE.md

**Last Updated:** 2026-05-02

## Mathematical Foundations

### Elo Rating System
```
E_team = 1 / (1 + 10^((opp_elo - team_elo) / 400))
new_elo = old_elo + K * (result - E_team)

K = 30, Home Advantage = +65 Elo, Bounds = [800, 2800]
Result encoding: H=2 (home win), D=1 (draw), A=0 (away win)
```

### Expected Goals (xG)
```
xG_home = (0.55 * avg_gf_home + 0.45 * avg_ga_away) * HOME_BOOST * elo_factor
xG_away = (0.55 * avg_gf_away + 0.45 * avg_ga_home) / elo_factor

HOME_BOOST = 1.15
elo_factor = 1 + (elo_diff / 5000)
Bounds: [0.3, 2.5]

NaN fallback: BASE_GOAL_RATE = 2.22 (used when team has no trailing stats,
e.g. promoted teams at season start). NOT a scaling factor in the formula.
```

### Poisson Goal Modeling
```
P(X = k) = (λ^k * e^-λ) / k!   where λ = xG

grid[h,a] = P(home=h) * P(away=a)   (9x9, up to MAX_GOALS=8)
normalize grid to sum=1.0

p_home_win = sum(grid[h>a])
p_draw     = sum(grid[h==a]) * POISSON_DRAW_ADJUSTMENT (0.85)
p_away_win = sum(grid[h<a])
p_home_win += HOME_ADVANTAGE_BOOST (0.08)
re-normalize to sum=1.0
```

### Shin Method (Odds → True Probabilities)
```
π_i = 1/odds_i   (implied probability)
p_i = ((√(z² + 4(1-z)π_i) - z) / (2(1-z)))²
Solve: Σp_i = 1 for z ∈ [0,1)

z = estimated proportion of insider traders
Output: Shin_Prob_H, Shin_Prob_D, Shin_Prob_A (used as ML features)
```

### Ensemble Prediction
```
blended = 0.6 * ML_proba + 0.4 * Poisson_proba
prediction = argmax(blended)
```

### Scoreline Generation
```
base: m_h = floor(xG_home), m_a = floor(xG_away)   ← Poisson mode, not round()

if max(p_h, p_d, p_a) >= 0.35:
  ml_pred==2 (home win): ensure m_h > m_a; if p_h >= 0.50, bump m_h += 1
  ml_pred==0 (away win): symmetric
  ml_pred==1 (draw):     m_h = m_a = max(m_h, m_a)

clamp to [0, 6]
```

Note: `round()` was the previous approach and caused all scores to be 1-1 because
Liga Profesional xG values (0.8–1.6) all round to 1. `floor()` gives 0 for weak
teams and 1 for average teams, producing realistic spread.

## Trailing Stats (Exponential Decay)

`compute_trailing_features()` uses exponential decay weighting over the last 8 matches:
- Recent matches weighted more than older ones
- `shift(1)` ensures no data leakage (current match excluded from its own stats)
- `get_all_teams_latest_stats()` reads `GF`/`GA` columns with fallback to `Home_GF`/`Away_GF`

## Calibration

Run `calibrate_poisson_params(matches_df)` from `src/stats_engine.py` to compare
predicted vs actual outcome frequencies and get a suggested `POISSON_DRAW_ADJUSTMENT`.
Do this at the start of each new season.

## Sofascore JSON Formats

Both formats are supported by `load_sofascore_data()`:

**Apify format:**
```json
{
  "teams": [{
    "standings": [{
      "rows": [{"team": {"name": "..."}, "points": 15, "goalsFor": 7, ...}]
    }]
  }]
}
```

**Manual format:**
```json
{
  "teams": [{"normalized": "TEAM NAME", "position": 1, "points": 15, ...}]
}
```

## ARG.csv Column Mapping

`apply_header_mapping()` normalizes football-data.co.uk headers to canonical names:

| Original | Canonical |
|----------|-----------|
| HomeTeam | HomeTeam |
| AwayTeam | AwayTeam |
| FTR | FullTimeResult |
| FTHG | Home_GF |
| FTAG | Away_GF |
| B365H | Odds_b365_H |
| B365D | Odds_b365_D |
| B365A | Odds_b365_A |

## Apify Integration

- Actor: `azzouzana/sofascore-scraper-pro`
- API token: `APIFY_API_TOKEN` environment variable
- Target: `https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155#tab:standings`
- Output: `src/sofascore_stats.json`

## Known Issues / Limitations

- `enrich_with_api_stats()` in `data_ingestion.py` is a documented no-op. API-Football team name fuzzy matching not implemented.
- TyC Sports scraper requires current-season URL via `--url`. HTML structure changes frequently.
- ML model accuracy (~35%) is near-random for a 3-class problem. Poisson component is more reliable for scoreline spread.
- Playoffs: model trained on regular season data only. Knockout dynamics not captured.
