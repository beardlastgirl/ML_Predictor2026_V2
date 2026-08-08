# Cold-start calibration and market probability utilities

import numpy as np
from scipy.optimize import minimize

from src.config import BAYESIAN_SHRINKAGE_C, LEAGUE_MEAN_XG


def get_season_start_weights(matchday: int) -> dict:
    """Feature weights for early-season noise reduction."""
    if matchday <= 3:
        return {"historical_apertura": 0.50, "market_shin": 0.40, "clausura_current": 0.10}
    if matchday <= 6:
        return {"historical_apertura": 0.25, "market_shin": 0.25, "clausura_current": 0.50}
    return {"historical_apertura": 0.05, "market_shin": 0.10, "clausura_current": 0.85}


def calculate_bayesian_shrunk_xg(
    team_raw_xg: float,
    matchday: int,
    league_mean_xg: float = LEAGUE_MEAN_XG,
    shrinkage_c: float = BAYESIAN_SHRINKAGE_C,
) -> float:
    """Shrink extreme early-season xG estimates toward the league mean."""
    if np.isnan(team_raw_xg) or matchday <= 0:
        return league_mean_xg
    return ((league_mean_xg * shrinkage_c) + (team_raw_xg * matchday)) / (shrinkage_c + matchday)


def extract_shin_probabilities(odds_h: float, odds_d: float, odds_a: float) -> np.ndarray:
    """Back out true probabilities from three-way bookmaker odds (Shin's method)."""
    inv_odds = 1.0 / np.array([odds_h, odds_d, odds_a], dtype=float)
    sum_inv = float(np.sum(inv_odds))

    def objective(z):
        z_val = float(z[0]) if hasattr(z, "__len__") else float(z)
        if z_val < 0 or z_val >= 1:
            return 1e6
        probs = [
            np.sqrt(z_val ** 2 + 4 * (1 - z_val) * (pi ** 2 / sum_inv))
            for pi in inv_odds
        ]
        return (1.0 - np.sum(probs)) ** 2

    res = minimize(objective, x0=[0.02], method="Nelder-Mead")
    z_opt = float(res.x[0])
    raw_probs = [
        np.sqrt(z_opt ** 2 + 4 * (1 - z_opt) * (pi ** 2 / sum_inv))
        for pi in inv_odds
    ]
    arr = np.array(raw_probs, dtype=float)
    total = arr.sum()
    if total <= 0:
        return np.array([1 / 3, 1 / 3, 1 / 3])
    return arr / total


def compute_team_matchdays(matches_df, season_col: str = "Season") -> tuple[np.ndarray, np.ndarray]:
    """Prior match counts per team within the current season (home/away sides)."""
    import pandas as pd

    df = matches_df.sort_values("Date").copy()
    if season_col not in df.columns:
        df[season_col] = "unknown"

    home_md = df.groupby([season_col, "HomeTeam"]).cumcount().values
    away_md = df.groupby([season_col, "AwayTeam"]).cumcount().values
    return home_md, away_md


def build_meta_xg_features(
    xg_home: np.ndarray,
    xg_away: np.ndarray,
    matchday_home: np.ndarray,
    matchday_away: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Bayesian-shrunk Poisson xG meta-features for gradient boosting."""
    meta_home = np.array([
        calculate_bayesian_shrunk_xg(h, int(max(m, 1)))
        for h, m in zip(xg_home, matchday_home)
    ])
    meta_away = np.array([
        calculate_bayesian_shrunk_xg(a, int(max(m, 1)))
        for a, m in zip(xg_away, matchday_away)
    ])
    return meta_home, meta_away
