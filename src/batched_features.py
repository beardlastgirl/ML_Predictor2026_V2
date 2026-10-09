"""Atomic timestamp-batch feature state for historical matches.

A batch is either one reliable kickoff timestamp or, where a date has an
unknown/unreliable kickoff time, the complete calendar day. The latter is
deliberately conservative: a result with an uncertain time cannot become
available to another match on that date.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config import BASE_ELO
from src.features import get_team_trailing_stats
from src.stats_engine import update_elo


def prepare_temporal_batches(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize timestamps and assign conservative chronological batch keys.

    The audit found 1,250 ``00:xx`` records. They are treated as unreliable,
    along with missing/malformed values; if one exists, all that date is one
    batch so uncertain order cannot leak results.
    """
    if "Date" not in matches_df:
        raise ValueError("Historical matches require a Date column for temporal features")
    result = matches_df.copy()
    dates = pd.to_datetime(result["Date"], errors="coerce").dt.normalize()
    if dates.isna().any():
        raise ValueError("Historical matches contain unparseable dates; temporal order is unknown")
    raw_time = (
        result["Time"].where(result["Time"].notna(), "").astype(str).str.strip()
        if "Time" in result else pd.Series("", index=result.index)
    )
    parsed_time = pd.to_datetime(raw_time, format="%H:%M", errors="coerce")
    unreliable = parsed_time.isna() | raw_time.str.match(r"^00:[0-5][0-9]$", na=False)
    has_unreliable = unreliable.groupby(dates).transform("any")
    reliable_timestamp = dates + (parsed_time - parsed_time.dt.normalize())
    result["_temporal_batch"] = reliable_timestamp.where(~has_unreliable, dates)
    result["_temporal_order"] = result["_temporal_batch"]
    result["_temporal_row_id"] = np.arange(len(result))
    result = result.sort_values(["_temporal_order", "_temporal_row_id"], kind="stable").reset_index(drop=True)
    # The identifier is used for feature alignment, so it must describe the
    # returned order rather than the caller's possibly-unsorted row order.
    result["_temporal_row_id"] = np.arange(len(result))
    return result


def _stable_batch_rows(batch: pd.DataFrame) -> pd.DataFrame:
    """Make post-batch state independent of input row order where possible."""
    home_col = "Home" if "Home" in batch.columns else "HomeTeam"
    away_col = "Away" if "Away" in batch.columns else "AwayTeam"
    identity = batch[[home_col, away_col]].astype(str).agg("\x1f".join, axis=1)
    return batch.assign(_stable_identity=identity).sort_values(
        ["_stable_identity", "_temporal_row_id"], kind="stable"
    )


def calculate_all_elo_ratings_batched(matches_df: pd.DataFrame, base_elo: int = BASE_ELO) -> Tuple[Dict[str, float], List[Dict]]:
    """
    Calculate Elo ratings with batch processing for same-timestamp matches.
    
    Matches sharing the same DateTime are processed as a batch:
    - All matches in batch use Elo from BEFORE the batch
    - Elo is updated AFTER all batch features are recorded
    
    Args:
        matches_df: DataFrame with Date, Time, Home/HomeTeam, Away/AwayTeam, Res/FullTimeResult columns
        base_elo: Starting Elo for new teams
    
    Returns:
        Tuple of (final_elo_ratings dict, elo_history list of dicts)
    """
    prepared = prepare_temporal_batches(matches_df)
    ratings: Dict[str, float] = {}
    history: List[Dict] = []
    for _, batch in prepared.groupby("_temporal_batch", sort=True):
        deltas: Dict[str, float] = defaultdict(float)
        for _, row in batch.iterrows():
            home = row["Home"] if "Home" in row else row["HomeTeam"]
            away = row["Away"] if "Away" in row else row["AwayTeam"]
            res = row["Res"] if "Res" in row else row.get("FullTimeResult", 1)
            home_elo, away_elo = ratings.get(home, base_elo), ratings.get(away, base_elo)
            history.append({"_temporal_row_id": row["_temporal_row_id"], "Date": row["Date"], "Home": home, "Away": away, "Home_Elo": home_elo, "Away_Elo": away_elo})
            new_home, new_away = update_elo(home_elo, away_elo, res)
            deltas[home] += new_home - home_elo
            deltas[away] += new_away - away_elo
        for team, delta in deltas.items():
            ratings[team] = float(np.clip(ratings.get(team, base_elo) + delta, 800, 2800))
    return ratings, history


def compute_trailing_features_batched(matches_df: pd.DataFrame, window: int = 8) -> pd.DataFrame:
    """
    Compute trailing features with batch processing for same-timestamp matches.
    
    Matches sharing the same DateTime are processed as a batch:
    - All matches in batch use trailing stats from BEFORE the batch
    - Trailing stats are updated AFTER all batch features are recorded
    
    Args:
        matches_df: DataFrame with Date, Time, Home/HomeTeam, Away/AwayTeam, GF/GA or HG/AG columns
        window: Number of trailing matches to consider
    
    Returns:
        DataFrame with trailing features added
    """
    prepared = prepare_temporal_batches(matches_df)
    team_history: Dict[str, List[Dict]] = defaultdict(list)
    trailing_features: List[Dict] = []
    for _, batch in prepared.groupby("_temporal_batch", sort=True):
        for _, row in batch.iterrows():
            home = row["Home"] if "Home" in row else row["HomeTeam"]
            away = row["Away"] if "Away" in row else row["AwayTeam"]
            home_stats, away_stats = get_team_trailing_stats(team_history[home], window), get_team_trailing_stats(team_history[away], window)
            trailing_features.append({"_temporal_row_id": row["_temporal_row_id"], "Home_Avg_GF": home_stats["avg_gf"], "Home_Avg_GA": home_stats["avg_ga"], "Home_Avg_GD": home_stats["avg_gd"], "Home_Form": home_stats["form"], "Home_Matches": home_stats["matches"], "Away_Avg_GF": away_stats["avg_gf"], "Away_Avg_GA": away_stats["avg_ga"], "Away_Avg_GD": away_stats["avg_gd"], "Away_Form": away_stats["form"], "Away_Matches": away_stats["matches"]})
        for _, row in _stable_batch_rows(batch).iterrows():
            home = row["Home"] if "Home" in row else row["HomeTeam"]
            away = row["Away"] if "Away" in row else row["AwayTeam"]
            gf = row["GF"] if "GF" in row and pd.notna(row["GF"]) else (row["HG"] if "HG" in row and pd.notna(row["HG"]) else 0)
            ga = row["GA"] if "GA" in row and pd.notna(row["GA"]) else (row["AG"] if "AG" in row and pd.notna(row["AG"]) else 0)
            team_history[home].append({"gf": gf, "ga": ga, "is_home": True})
            team_history[away].append({"gf": ga, "ga": gf, "is_home": False})
    feature_frame = pd.DataFrame(trailing_features).set_index("_temporal_row_id")
    result = prepared.set_index("_temporal_row_id")
    for column in feature_frame:
        result[column] = feature_frame[column]
    return result.drop(columns=["_temporal_batch", "_temporal_order"], errors="ignore").reset_index(drop=True)
