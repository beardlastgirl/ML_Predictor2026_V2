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
    form = points / len(recent) if len(recent) > 0 else np.nan
    return {
        "avg_gf": avg_gf,
        "avg_ga": avg_ga,
        "avg_gd": avg_gd,
        "form": form,
        "matches": len(recent),
    }

def compute_trailing_features(matches_df, window=8):
    """Compute trailing-average features for each team chronologically using vectorization."""
    log_info(f"Computing trailing features with window={window} (vectorized)...")
    
    # Create a long-format dataframe with one row per team per match
    df = matches_df.copy().sort_values("Date")
    
    # Home team entries
    h_df = df[["Date", "Home", "GF", "GA"]].rename(columns={"Home": "Team", "GF": "Goals_For", "GA": "Goals_Against"})
    h_df["Is_Home"] = True
    h_df["Match_ID"] = df.index
    
    # Away team entries
    a_df = df[["Date", "Away", "GA", "GF"]].rename(columns={"Away": "Team", "GA": "Goals_For", "GF": "Goals_Against"})
    a_df["Is_Home"] = False
    a_df["Match_ID"] = df.index
    
    # Combine and sort
    long_df = pd.concat([h_df, a_df]).sort_values(["Team", "Date"])
    
    # Calculate points
    long_df["Points"] = 0
    long_df.loc[long_df["Goals_For"] > long_df["Goals_Against"], "Points"] = 3
    long_df.loc[long_df["Goals_For"] == long_df["Goals_Against"], "Points"] = 1
    
    # Group by team and calculate rolling averages
    # We shift(1) so the average DOES NOT include the current match
    gb = long_df.groupby("Team")
    
    long_df["Avg_GF"] = gb["Goals_For"].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    long_df["Avg_GA"] = gb["Goals_Against"].transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    long_df["Form"] = gb["Points"].transform(lambda x: x.shift(1).rolling(window, min_periods=1).sum() / window)
    long_df["Matches"] = gb.cumcount()
    long_df.loc[long_df["Matches"] > window, "Matches"] = window
    
    long_df["Avg_GD"] = long_df["Avg_GF"] - long_df["Avg_GA"]
    
    # Split back into home and away and join to original
    h_features = long_df[long_df["Is_Home"]].set_index("Match_ID")
    a_features = long_df[~long_df["Is_Home"]].set_index("Match_ID")
    
    for col in ["Avg_GF", "Avg_GA", "Avg_GD", "Form", "Matches"]:
        df[f"Home_{col}"] = h_features[col]
        df[f"Away_{col}"] = a_features[col]
        
    log_ok(f"Trailing features computed for {len(df)} matches")
    return df

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
