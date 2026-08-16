# Trailing-average feature engineering

import numpy as np
import pandas as pd
from src.config import TOURNAMENT_TRANSITION_DECAY
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

def _apply_tournament_decay(long_df, season_col="Season", decay=TOURNAMENT_TRANSITION_DECAY):
    """Multiply prior-season weights by ``decay`` at every season transition.

    The long-form frame must already be sorted by (Team, Date). For each team
    we walk through its rows; the moment ``Season`` changes we scale *all
    previously-emitted weight rows* for that team by ``decay``. Subsequent
    rows within the new season use a fresh ``np.exp(np.linspace(-1, 0, N))``
    weight vector. The returned weight vector has the same length as
    ``long_df`` and can be supplied to the EWMA helper in place of the default
    uniform weights.
    """
    if season_col not in long_df.columns or decay >= 1.0 or decay <= 0.0:
        # Without season info (e.g. unit tests) or with a non-shrinking decay
        # we fall back to the original per-team exponential weights.
        weights = np.empty(len(long_df), dtype=float)
        for team, idx in long_df.groupby("Team").indices.items():
            n = len(idx)
            weights[idx] = np.exp(np.linspace(-1, 0, n))
        return pd.Series(weights, index=long_df.index)

    weights = np.empty(len(long_df), dtype=float)
    for team, group in long_df.groupby("Team"):
        idx = group.index.to_numpy()
        seasons = group[season_col].to_numpy()
        n = len(group)
        # Per-segment weight vectors, each segment = one contiguous season
        # within this team's history. Earlier segments are scaled by the
        # decay factor raised to the number of seasons between them and the
        # most recent segment.
        segments = []
        start = 0
        for i in range(1, n):
            if seasons[i] != seasons[i - 1]:
                segments.append((start, i))
                start = i
        segments.append((start, n))

        n_segments = len(segments)
        team_weights = np.empty(n, dtype=float)
        for seg_i, (seg_start, seg_end) in enumerate(segments):
            seg_len = seg_end - seg_start
            # Distance (in seasons) from this segment to the most recent
            # segment for the team. The most recent segment itself is not
            # scaled; every earlier segment is multiplied by decay^distance.
            distance = n_segments - 1 - seg_i
            seg_w = np.exp(np.linspace(-1, 0, seg_len)) * (decay ** distance)
            team_weights[seg_start:seg_end] = seg_w
        weights[idx] = team_weights

    return pd.Series(weights, index=long_df.index)


def compute_trailing_features(matches_df, window=8, until_row=None):
    """Compute trailing-average features for each team chronologically.

    Args:
        matches_df: DataFrame with columns Date, HomeTeam, AwayTeam, GF, GA
            (and optionally Season). Assumed chronologically sorted; will be
            re-sorted defensively.
        window: Trailing-window size.
        until_row: Optional int. If given, only the first ``until_row`` rows
            of ``matches_df`` (in sorted-chronological order) participate in
            the EWMA computation. Rows at index ``>= until_row`` receive
            "as-of cutoff" features copied from the most recent replayed row
            of their team. Used by time-series CV to prevent validation rows
            from being influenced by future matches.

    Returns:
        The input DataFrame (re-sorted chronologically) with columns
        Home_Avg_GF, Home_Avg_GA, Home_Avg_GD, Home_Form, Home_Matches,
        Away_Avg_GF, Away_Avg_GA, Away_Avg_GD, Away_Form, Away_Matches added.
    """
    log_info(f"Computing trailing features with window={window} (vectorized)...")

    df = matches_df.copy().sort_values("Date").reset_index(drop=True)

    if until_row is None or until_row >= len(df):
        replayed = df
        tail = df.iloc[0:0]  # empty
    else:
        replayed = df.iloc[:until_row].copy()
        tail = df.iloc[until_row:].copy()

    # Create a long-format dataframe with one row per team per match
    h_df = replayed[["Date", "HomeTeam", "GF", "GA"]].rename(
        columns={"HomeTeam": "Team", "GF": "Goals_For", "GA": "Goals_Against"}
    )
    h_df["Is_Home"] = True
    h_df["Match_ID"] = replayed.index

    a_df = replayed[["Date", "AwayTeam", "GA", "GF"]].rename(
        columns={"AwayTeam": "Team", "GA": "Goals_For", "GF": "Goals_Against"}
    )
    a_df["Is_Home"] = False
    a_df["Match_ID"] = replayed.index

    # Combine and sort
    long_df = pd.concat([h_df, a_df]).sort_values(["Team", "Date"])

    # Calculate points
    long_df["Points"] = 0
    long_df.loc[long_df["Goals_For"] > long_df["Goals_Against"], "Points"] = 3
    long_df.loc[long_df["Goals_For"] == long_df["Goals_Against"], "Points"] = 1

    # Propagate Season column onto the long form so the tournament decay can
    # detect transitions. A single match yields one Season value per row in
    # the wide frame; we map it onto both the home and away long-form rows.
    if "Season" in replayed.columns:
        season_map = replayed["Season"]
        long_df = long_df.merge(
            season_map.rename("Season").reset_index().rename(columns={"index": "Match_ID"}),
            on="Match_ID",
            how="left",
        )

    # Group by team and calculate rolling averages
    # We shift(1) so the average DOES NOT include the current match
    gb = long_df.groupby("Team")

    # Define decay function. Accepts an optional weights vector to support
    # TOURNAMENT_TRANSITION_DECAY across season boundaries.
    def exponential_decay(x, window, weights=None):
        if weights is None:
            weights = pd.Series(np.exp(np.linspace(-1, 0, len(x))), index=x.index)
        return (
            x.multiply(weights)
            .rolling(window, min_periods=1)
            .sum()
            / weights.rolling(window, min_periods=1).sum()
        )

    # Tournament-aware weights: scale each team's prior-season EWMA weights by
    # TOURNAMENT_TRANSITION_DECAY at every season boundary. Falls back to the
    # original exp-spaced weights if Season is missing or decay == 1.
    weights = _apply_tournament_decay(long_df)

    long_df["Avg_GF"] = gb["Goals_For"].transform(
        lambda x: x.shift(1).pipe(
            lambda s: exponential_decay(s, window, weights.loc[s.index])
        )
    )
    long_df["Avg_GA"] = gb["Goals_Against"].transform(
        lambda x: x.shift(1).pipe(
            lambda s: exponential_decay(s, window, weights.loc[s.index])
        )
    )

    # Form remains standard sum/window — it was already fold-safe because the
    # long-form frame is sorted by (Team, Date) and we shift(1) inside each
    # team group.
    long_df["Form"] = (
        gb["Points"].transform(lambda x: x.shift(1).rolling(window, min_periods=1).sum() / window)
    )
    long_df["Matches"] = gb.cumcount()
    long_df.loc[long_df["Matches"] > window, "Matches"] = window

    long_df["Avg_GD"] = long_df["Avg_GF"] - long_df["Avg_GA"]

    # Split back into home and away and join onto the replayed slice.
    h_features = long_df[long_df["Is_Home"]].set_index("Match_ID")
    a_features = long_df[~long_df["Is_Home"]].set_index("Match_ID")

    feature_cols = ["Avg_GF", "Avg_GA", "Avg_GD", "Form", "Matches"]
    for col in feature_cols:
        replayed[f"Home_{col}"] = h_features[col]
        replayed[f"Away_{col}"] = a_features[col]

    # ---- "as-of cutoff" tail ----
    # For validation rows beyond ``until_row`` we propagate the most recent
    # replayed feature vector for each (home_team, away_team) pair so that
    # downstream code can consume a single DataFrame of features without
    # special-casing fold boundaries. Each tail row gets features computed
    # strictly from matches that occurred at or before the cutoff row.
    if not tail.empty:
        # Most-recent replayed feature per team (home + away views).
        last_per_team = (
            long_df.sort_values(["Team", "Date"])
            .groupby("Team")
            .tail(1)
            .set_index("Team")
        )
        for col in feature_cols:
            home_lookup = last_per_team[col]
            away_lookup = last_per_team[col]
            tail[f"Home_{col}"] = tail["HomeTeam"].map(home_lookup)
            tail[f"Away_{col}"] = tail["AwayTeam"].map(away_lookup)
        df = pd.concat([replayed, tail], ignore_index=False)
        # Restore original chronological ordering using the index we built
        # at the top.
        df = df.sort_index()
    else:
        df = replayed

    log_ok(f"Trailing features computed for {len(df)} matches")
    return df

def get_all_teams_latest_stats(matches_df, window=8):
    """Get latest trailing stats for all teams from historical match data."""
    if matches_df is None or matches_df.empty:
        return {}
    
    team_history = {}
    df = matches_df.sort_values("Date")
    
    for _, row in df.iterrows():
        home_team = row["HomeTeam"]
        away_team = row["AwayTeam"]
        
        # Resolve goal columns: prefer GF/GA, fall back to Home_GF/Away_GF
        if "GF" in row and "GA" in row and (row.get("GF", 0) != 0 or row.get("GA", 0) != 0):
            home_gf = row.get("GF", 0)
            away_gf = row.get("GA", 0)
        elif "Home_GF" in row and "Away_GF" in row:
            home_gf = row.get("Home_GF", 0)
            away_gf = row.get("Away_GF", 0)
        else:
            home_gf = 0
            away_gf = 0
        
        if home_team not in team_history:
            team_history[home_team] = []
        if away_team not in team_history:
            team_history[away_team] = []
            
        team_history[home_team].append({"gf": home_gf, "ga": away_gf})
        team_history[away_team].append({"gf": away_gf, "ga": home_gf})
    
    latest_stats = {}
    for team, history in team_history.items():
        latest_stats[team] = get_team_trailing_stats(history, window)
    
    return latest_stats

def get_team_stats_from_history(matches_df, team_name, window=8):
    """Get current trailing stats for a team from historical match data."""
    if matches_df is None or matches_df.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}
    
    # This is still here for backward compatibility but using get_all_teams_latest_stats is preferred
    team_matches = matches_df[(matches_df["HomeTeam"] == team_name) | (matches_df["AwayTeam"] == team_name)].sort_values("Date")
    if team_matches.empty:
        return {"avg_gf": np.nan, "avg_ga": np.nan, "avg_gd": np.nan, "form": np.nan, "matches": 0}
        
    history = []
    for _, row in team_matches.iterrows():
        if row["HomeTeam"] == team_name:
            history.append({"gf": row.get("GF", 0), "ga": row.get("GA", 0)})
        else:
            history.append({"gf": row.get("GA", 0), "ga": row.get("GF", 0)})
            
    return get_team_trailing_stats(history, window)
