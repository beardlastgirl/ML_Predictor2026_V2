# Trailing-average feature engineering

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union
from src.utils import log_info, log_ok


def get_team_trailing_stats(history: List[Dict], window: int) -> Dict[str, Union[float, int]]:
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
    avg_gf = float(np.mean(gf_list))
    avg_ga = float(np.mean(ga_list))
    avg_gd = avg_gf - avg_ga
    points = 0
    for m in recent:
        gf, ga = m["gf"], m["ga"]
        if gf > ga:
            points += 3
        elif gf == ga:
            points += 1
    form = float(points / len(recent)) if len(recent) > 0 else np.nan
    return {
        "avg_gf": avg_gf,
        "avg_ga": avg_ga,
        "avg_gd": avg_gd,
        "form": form,
        "matches": len(recent),
    }


def compute_trailing_features(matches_df: pd.DataFrame, window: int = 8) -> pd.DataFrame:
    """Compute trailing-average features for each team chronologically."""
    # Public compatibility entry point.  Keep direct callers on the same
    # atomic timestamp semantics as the production pipeline.
    from src.batched_features import compute_trailing_features_batched
    return compute_trailing_features_batched(matches_df, window)


def get_all_teams_latest_stats(matches_df: pd.DataFrame, window: int = 8) -> Dict[str, Dict[str, Union[float, int]]]:
    """Get latest trailing stats for all teams from historical match data."""
    if matches_df is None or matches_df.empty:
        return {}

    team_history: Dict[str, List[Dict]] = {}
    # Sort by date to ensure chronological order. Stable sort preserves the
    # canonical timestamp-batch order (prepare_temporal_batches) within a date
    # when the caller passes pipeline-ordered data.
    df = matches_df.sort_values("Date", kind="stable")

    for _, row in df.iterrows():
        home_team = row["Home"] if "Home" in row else row["HomeTeam"]
        away_team = row["Away"] if "Away" in row else row["AwayTeam"]

        if home_team not in team_history:
            team_history[home_team] = []
        if away_team not in team_history:
            team_history[away_team] = []

        team_history[home_team].append({"gf": row.get("GF", 0), "ga": row.get("GA", 0)})
        team_history[away_team].append({"gf": row.get("GA", 0), "ga": row.get("GF", 0)})

    latest_stats: Dict[str, Dict[str, Union[float, int]]] = {}
    for team, history in team_history.items():
        latest_stats[team] = get_team_trailing_stats(history, window)

    return latest_stats


def get_team_stats_from_history(matches_df: pd.DataFrame, team_name: str, window: int = 8) -> Dict[str, Union[float, int]]:
    """Get current trailing stats for a team from historical match data."""
    if matches_df is None or matches_df.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}

    # This is still here for backward compatibility but using get_all_teams_latest_stats is preferred
    home_col = "Home" if "Home" in matches_df.columns else "HomeTeam"
    away_col = "Away" if "Away" in matches_df.columns else "AwayTeam"
    team_matches = matches_df[(matches_df[home_col] == team_name) | (matches_df[away_col] == team_name)].sort_values("Date")
    if team_matches.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}

    history: List[Dict] = []
    for _, row in team_matches.iterrows():
        h_team = row["Home"] if "Home" in row else row["HomeTeam"]
        if h_team == team_name:
            history.append({"gf": row.get("GF", 0), "ga": row.get("GA", 0)})
        else:
            history.append({"gf": row.get("GA", 0), "ga": row.get("GF", 0)})

    return get_team_trailing_stats(history, window)
