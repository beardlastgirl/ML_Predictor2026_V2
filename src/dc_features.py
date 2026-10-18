"""
src/dc_features.py
Phase 2.0.2 — Venue-Split Raw Feature Path for Dixon-Coles Stage 1

WHY THIS MODULE EXISTS
----------------------
The Phase 2.0 DC model used venue-MIXED trailing averages:
  Home_Avg_GF = mean HG over all matches (home + away)
  Away_Avg_GF = mean AG over all matches (home + away)

These inherit the real-world venue effect as a near-constant bias: home teams
always score more at home, away teams always score less away. The Stage 1
Poisson regressors absorb this bias into the predictions, producing a
structural λ_h/λ_a gap of ~0.33 goals on every match regardless of how
evenly-matched the teams are. This collapses P(Draw) into a flat 24% prior.

THE FIX
-------
Venue-split features separate the venue effect from team quality:
  DC_Home_Att  = mean HG when playing at home  (home attack context)
  DC_Home_Def  = mean AG when playing at home  (home defence under real pressure)
  DC_Away_Att  = mean AG when playing away     (away attack under real pressure)
  DC_Away_Def  = mean HG when playing away     (away defence context)

The Stage 1 models then learn:
  λ_home ~ DC_Home_Att, DC_Away_Def, Elo_Diff
  λ_away ~ DC_Away_Att, DC_Home_Def, Elo_Diff

When two evenly-matched teams meet (Elo_Diff ≈ 0), λ_h ≈ DC_Home_Att and
λ_a ≈ DC_Away_Att. If the home team concedes a lot at home AND the away
team attacks well away, the λ gap narrows — potentially P(Draw) rises above
25%. This creates match-level variation, not a flat prior.

FALLBACK
--------
If a team has fewer than VENUE_SPLIT_MIN_MATCHES venue-specific entries,
the feature falls back to the overall trailing average (same convention as
_venue_stats in batched_features.py).

BATCH ISOLATION
---------------
Uses the same conservative temporal batching as compute_trailing_features_batched:
matches sharing an uncertain kickoff time are processed as a single batch,
so no intra-batch result leakage occurs.

CLASS ENCODING: 0=Away, 1=Draw, 2=Home (unchanged).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

import numpy as np
import pandas as pd

from src.batched_features import (
    prepare_temporal_batches,
    _stable_batch_rows,
)
from src.config import VENUE_SPLIT_MIN_MATCHES
from src.features import get_team_trailing_stats

WINDOW = 8  # trailing window — keep consistent with production

# Feature names produced by build_dc_features()
DC_FEATURE_NAMES = [
    "DC_Home_Att",   # home team: avg HG scored at home
    "DC_Home_Def",   # home team: avg AG conceded at home
    "DC_Away_Att",   # away team: avg AG scored away
    "DC_Away_Def",   # away team: avg HG conceded away
    "Elo_Diff",      # home Elo minus away Elo (already in matches_feat)
]

# Stage 1 model feature sets (passed to PoissonRegressor)
DC_HOME_FEATURES = ["DC_Home_Att", "DC_Away_Def", "Elo_Diff"]
DC_AWAY_FEATURES = ["DC_Away_Att", "DC_Home_Def", "Elo_Diff"]
DC_ALL_FEATURES = sorted(set(DC_HOME_FEATURES + DC_AWAY_FEATURES))


def _venue_trailing_avg(history: List[Dict], is_home: bool,
                        key: str, window: int) -> float:
    """
    Trailing average of `key` from venue-matched history.

    Filters history to entries where is_home matches, then computes the
    average of the last `window` entries. Falls back to overall trailing
    average when venue-specific count < VENUE_SPLIT_MIN_MATCHES.

    Parameters
    ----------
    history : list of dicts with keys 'gf', 'ga', 'is_home'
    is_home : True for home-venue matches, False for away-venue matches
    key : 'gf' or 'ga'
    window : trailing window size
    """
    if not history:
        return np.nan

    venue_history = [m for m in history if m.get("is_home") == is_home]

    if len(venue_history) >= VENUE_SPLIT_MIN_MATCHES:
        source = venue_history
    else:
        source = history  # fallback to mixed

    recent = source[-window:]
    return float(np.mean([m[key] for m in recent]))


def build_dc_features(matches_df: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """
    Compute venue-split raw trailing features for DC Stage 1.

    Adds columns to `matches_df`:
      DC_Home_Att  home team avg goals scored at home (last `window` home games)
      DC_Home_Def  home team avg goals conceded at home
      DC_Away_Att  away team avg goals scored away (last `window` away games)
      DC_Away_Def  away team avg goals conceded away

    Elo_Diff must already be present in the DataFrame (from build_features).

    All columns satisfy the same NaN contract as compute_trailing_features_batched:
    NaN when history is empty, finite value otherwise (or fallback to overall avg).

    Batch isolation: matches sharing an uncertain kickoff are processed as a
    single batch; feature state is frozen before the batch, updated after.

    Parameters
    ----------
    matches_df : DataFrame after pipeline load_data() + Elo computation.
                 Must have columns: Date, Time, Home, Away, HG, AG.
    window : trailing window size.

    Returns
    -------
    DataFrame with DC_Home_Att, DC_Home_Def, DC_Away_Att, DC_Away_Def columns
    added (or overwritten if already present).
    """
    prepared = prepare_temporal_batches(matches_df)

    # Per-team history: list of dicts {gf, ga, is_home}
    team_history: Dict[str, List[Dict]] = defaultdict(list)
    dc_feats: List[Dict] = []

    for _, batch in prepared.groupby("_temporal_batch", sort=True):
        # --- RECORD state before this batch ---
        for _, row in batch.iterrows():
            home = row["Home"] if "Home" in row else row["HomeTeam"]
            away = row["Away"] if "Away" in row else row["AwayTeam"]

            # Home team's venue-split home stats
            h_att = _venue_trailing_avg(team_history[home], is_home=True,
                                        key="gf", window=window)
            h_def = _venue_trailing_avg(team_history[home], is_home=True,
                                        key="ga", window=window)

            # Away team's venue-split away stats
            a_att = _venue_trailing_avg(team_history[away], is_home=False,
                                        key="gf", window=window)
            a_def = _venue_trailing_avg(team_history[away], is_home=False,
                                        key="ga", window=window)

            dc_feats.append({
                "_temporal_row_id": row["_temporal_row_id"],
                "DC_Home_Att": h_att,
                "DC_Home_Def": h_def,
                "DC_Away_Att": a_att,
                "DC_Away_Def": a_def,
            })

        # --- UPDATE history after the entire batch (stable order to be
        #     consistent with compute_trailing_features_batched) ---
        for _, row in _stable_batch_rows(batch).iterrows():
            home = row["Home"] if "Home" in row else row["HomeTeam"]
            away = row["Away"] if "Away" in row else row["AwayTeam"]

            hg = int(row["HG"]) if pd.notna(row.get("HG")) else 0
            ag = int(row["AG"]) if pd.notna(row.get("AG")) else 0

            # Home team played at home: gf=HG, ga=AG, is_home=True
            team_history[home].append({"gf": hg, "ga": ag, "is_home": True})
            # Away team played away: gf=AG, ga=HG, is_home=False
            team_history[away].append({"gf": ag, "ga": hg, "is_home": False})

    feat_df = (
        pd.DataFrame(dc_feats)
        .set_index("_temporal_row_id")
        .reindex(prepared["_temporal_row_id"])
    )

    result = prepared.set_index("_temporal_row_id").copy()
    for col in ["DC_Home_Att", "DC_Home_Def", "DC_Away_Att", "DC_Away_Def"]:
        result[col] = feat_df[col].values

    return (
        result
        .drop(columns=["_temporal_batch", "_temporal_order"], errors="ignore")
        .reset_index(drop=True)
    )
