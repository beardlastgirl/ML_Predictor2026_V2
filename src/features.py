# Trailing-average feature engineering

import numpy as np
import pandas as pd
from src.utils import log_info, log_ok

def get_team_trailing_stats(history, window):
    """Calculate trailing statistics from team history."""
    if not history:
        return {
            "avg_gf": np.nan,
            "avg_ga": np.nan,
            "avg_gd": np.nan,
            "form": np.nan,
            "matches": 0,
        }
    recent = history[-window:]
    gf_list = [m["gf"] for m in recent]
    ga_list = [m["ga"] for m in recent]
    avg_gf = np.mean(gf_list)
    avg_ga = np.mean(ga_list)
    avg_gd = avg_gf - avg_ga
    points = 0
    for m in recent:
        gf, ga = m["gf"], m["ga"]
        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1
    form = points / len(recent)
    return {
        "avg_gf": avg_gf,
        "avg_ga": avg_ga,
        "avg_gd": avg_gd,
        "form": form,
        "matches": len(recent),
    }

def compute_trailing_features(matches_df, window=8):
    """Compute trailing-average features for each team chronologically."""
    log_info(f"Computing trailing features with window={window}...")
    team_history = {}
    trailing_features = []
    for idx, row in matches_df.iterrows():
        home_team = row["Home"]
        away_team = row["Away"]
        date = row["Date"]
        home_stats = get_team_trailing_stats(team_history.get(home_team, []), window)
        away_stats = get_team_trailing_stats(team_history.get(away_team, []), window)
        if home_team not in team_history:
            team_history[home_team] = []
        if away_team not in team_history:
            team_history[away_team] = []
        team_history[home_team].append({"date": date, "gf": row.get("GF", 0), "ga": row.get("GA", 0), "is_home": True})
        team_history[away_team].append({"date": date, "gf": row.get("GA", 0), "ga": row.get("GF", 0), "is_home": False})
        trailing_features.append({
            "idx": idx,
            "Home_Avg_GF": home_stats["avg_gf"],
            "Home_Avg_GA": home_stats["avg_ga"],
            "Home_Avg_GD": home_stats["avg_gd"],
            "Home_Form": home_stats["form"],
            "Home_Matches": home_stats["matches"],
            "Away_Avg_GF": away_stats["avg_gf"],
            "Away_Avg_GA": away_stats["avg_ga"],
            "Away_Avg_GD": away_stats["avg_gd"],
            "Away_Form": away_stats["form"],
            "Away_Matches": away_stats["matches"],
        })
    traildf = pd.DataFrame(trailing_features)
    traildf = traildf.set_index("idx")
    result = matches_df.copy()
    for col in traildf.columns:
        result[col] = traildf[col]
    log_ok(f"Trailing features computed for {len(result)} matches")
    return result

def get_all_teams_latest_stats(matches_df, window=8):
    """Get latest trailing stats for all teams from historical match data."""
    if matches_df is None or matches_df.empty:
        return {}
    
    team_history = {}
    # Sort by date to ensure chronological order
    df = matches_df.sort_values("Date")
    
    for _, row in df.iterrows():
        home_team = row["Home"]
        away_team = row["Away"]
        
        if home_team not in team_history:
            team_history[home_team] = []
        if away_team not in team_history:
            team_history[away_team] = []
            
        team_history[home_team].append({"gf": row.get("GF", 0), "ga": row.get("GA", 0)})
        team_history[away_team].append({"gf": row.get("GA", 0), "ga": row.get("GF", 0)})
    
    latest_stats = {}
    for team, history in team_history.items():
        latest_stats[team] = get_team_trailing_stats(history, window)
    
    return latest_stats

def get_team_stats_from_history(matches_df, team_name, window=8):
    """Get current trailing stats for a team from historical match data."""
    if matches_df is None or matches_df.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}
    
    # This is still here for backward compatibility but using get_all_teams_latest_stats is preferred
    team_matches = matches_df[(matches_df["Home"] == team_name) | (matches_df["Away"] == team_name)].sort_values("Date")
    if team_matches.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}
        
    history = []
    for _, row in team_matches.iterrows():
        if row["Home"] == team_name:
            history.append({"gf": row.get("GF", 0), "ga": row.get("GA", 0)})
        else:
            history.append({"gf": row.get("GA", 0), "ga": row.get("GF", 0)})
            
    return get_team_trailing_stats(history, window)
