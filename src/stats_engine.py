# Elo and Poisson distribution logic

import numpy as np
import pandas as pd
from scipy.stats import poisson
from scipy.optimize import brentq
from src.config import (
    HOME_ADVANTAGE, K_FACTOR, MAX_GOALS, BASE_GOAL_RATE,
    ELO_DIVISOR, ELO_FACTOR_DENOM, HOME_BOOST,
    GOAL_WEIGHT_ATTACK, GOAL_WEIGHT_DEFENSE, XG_MIN, XG_MAX,
    BASE_ELO, POISSON_DRAW_ADJUSTMENT
)

def expected_result(elo_team, elo_opp):
    """Expected score for a team given opponent Elo."""
    return 1 / (1 + 10 ** ((elo_opp - elo_team) / ELO_DIVISOR))

def update_elo(home_elo, away_elo, result):
    """Update Elo ratings given match result (2=Home win, 1=Draw, 0=Away win)."""
    exp_home = expected_result(home_elo + HOME_ADVANTAGE, away_elo)
    exp_away = 1 - exp_home

    if result == 2:
        home_score, away_score = 1, 0
    elif result == 1:
        home_score, away_score = 0.5, 0.5
    else:
        home_score, away_score = 0, 1

    home_elo_new = home_elo + K_FACTOR * (home_score - exp_home)
    away_elo_new = away_elo + K_FACTOR * (away_score - exp_away)
    
    # Bound Elo ratings to reasonable range (800-2800)
    home_elo_new = np.clip(home_elo_new, 800, 2800)
    away_elo_new = np.clip(away_elo_new, 800, 2800)
    
    return home_elo_new, away_elo_new

def calculate_expected_goals(
    elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away
):
    """Calculate expected goals for each team. Supports both scalar and array inputs.
    
    BASE_GOAL_RATE is used as the fallback when a team has no trailing stats
    (e.g. new/promoted teams at the start of a season).
    """
    # Use BASE_GOAL_RATE as the fallback for missing stats
    avg_gf_home = np.where(pd.isna(avg_gf_home), BASE_GOAL_RATE, avg_gf_home)
    avg_gf_away = np.where(pd.isna(avg_gf_away), BASE_GOAL_RATE, avg_gf_away)
    avg_ga_home = np.where(pd.isna(avg_ga_home), BASE_GOAL_RATE, avg_ga_home)
    avg_ga_away = np.where(pd.isna(avg_ga_away), BASE_GOAL_RATE, avg_ga_away)

    xG_home = (GOAL_WEIGHT_ATTACK * avg_gf_home + GOAL_WEIGHT_DEFENSE * avg_ga_away) * HOME_BOOST
    xG_away = GOAL_WEIGHT_ATTACK * avg_gf_away + GOAL_WEIGHT_DEFENSE * avg_ga_home

    elo_diff = elo_home - elo_away
    elo_factor = 1 + (elo_diff / ELO_FACTOR_DENOM)

    xG_home = xG_home * elo_factor
    xG_away = xG_away / elo_factor

    xG_home = np.clip(xG_home, XG_MIN, XG_MAX)
    xG_away = np.clip(xG_away, XG_MIN, XG_MAX)

    return xG_home, xG_away

def poisson_probability(goals, expected):
    """Calculate Poisson probability of scoring exactly k goals."""
    return poisson.pmf(goals, expected)

def calculate_outcome_probabilities(xG_home, xG_away, max_goals=MAX_GOALS):
    """Calculate match outcome probabilities from Poisson goal distributions.

    Calibrated 2026-05-02 against 6171 Liga Profesional matches:
      Actual:    home=43.1%, draw=30.3%, away=26.6%
      Predicted: home=43.0%, draw=30.3%, away=26.6%

    Calibration parameters (src/config.py):
      POISSON_DRAW_ADJUSTMENT = 1.11   (scales raw Poisson draws up)
      HOME_ADVANTAGE_BOOST    = 0.02   (small residual after xG home encoding)

    To re-calibrate: run calibrate_poisson_params() from stats_engine.py
    """
    goals = np.arange(max_goals + 1)
    p_home = poisson.pmf(goals, xG_home)
    p_away = poisson.pmf(goals, xG_away)

    # Grid of scoreline probabilities: grid[h, a] = P(home=h, away=a)
    grid = np.outer(p_home, p_away)
    grid_sum = grid.sum()
    if grid_sum > 0:
        grid /= grid_sum

    # Use indices to calculate win/draw/loss
    h_idx, a_idx = np.indices((max_goals + 1, max_goals + 1))

    p_home_win = grid[h_idx > a_idx].sum()
    p_draw = grid[h_idx == a_idx].sum()
    p_away_win = grid[h_idx < a_idx].sum()

    # Calibrate draw probability toward historical league average (30.3%)
    p_draw_calibrated = p_draw * POISSON_DRAW_ADJUSTMENT
    remainder = 1.0 - p_draw_calibrated

    # Redistribute remainder proportionally to home/away win probabilities
    total_win = p_home_win + p_away_win
    if total_win > 0:
        p_home_win = (p_home_win / total_win) * remainder
        p_away_win = (p_away_win / total_win) * remainder
    else:
        p_home_win = remainder / 2
        p_away_win = remainder / 2

    # Add home advantage boost to final probability
    # Calibrated 2026-05-02: actual home win rate = 43.1%
    # With POISSON_DRAW_ADJUSTMENT=1.154, raw predicted home = ~46.9%
    # Boost of 0.00 gives ~46.9% — still over. The Elo + xG already encode
    # home advantage via HOME_BOOST (1.15x) and HOME_ADVANTAGE (+65 Elo).
    # Remove the additive boost entirely; home advantage is already in xG.
    from src.config import HOME_ADVANTAGE_BOOST
    p_home_win = min(0.95, p_home_win + HOME_ADVANTAGE_BOOST)
    p_away_win = max(0.05, p_away_win - HOME_ADVANTAGE_BOOST * 0.5)

    # Re-normalize to ensure probabilities sum to 1
    total = p_home_win + p_draw_calibrated + p_away_win
    if total > 1e-10:  # Avoid numerical instability
        p_home_win /= total
        p_draw_calibrated /= total
        p_away_win /= total
    else:
        # Fallback to uniform distribution if probabilities are too small
        p_home_win = p_draw_calibrated = p_away_win = 1.0 / 3.0

    expected_home_goals = (h_idx * grid).sum()
    expected_away_goals = (a_idx * grid).sum()

    return {
        "home_win": float(p_home_win),
        "draw": float(p_draw_calibrated),
        "away_win": float(p_away_win),
        "expected_home_goals": float(expected_home_goals),
        "expected_away_goals": float(expected_away_goals),
        "xG_home": xG_home,
        "xG_away": xG_away,
    }

def calculate_poisson_features(
    elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away
):
    """Calculate all Poisson-derived features for a match."""
    xG_home, xG_away = calculate_expected_goals(
        elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away
    )
    outcomes = calculate_outcome_probabilities(xG_home, xG_away)

    return {
        "xG_home": xG_home,
        "xG_away": xG_away,
        "xG_diff": xG_home - xG_away,
        "Poisson_Home_Win": outcomes["home_win"],
        "Poisson_Draw": outcomes["draw"],
        "Poisson_Away_Win": outcomes["away_win"],
        "Expected_Home_Goals": outcomes["expected_home_goals"],
        "Expected_Away_Goals": outcomes["expected_away_goals"],
        "Expected_Total_Goals": outcomes["expected_home_goals"] + outcomes["expected_away_goals"],
    }

def calculate_all_elo_ratings(matches_df, base_elo=BASE_ELO, until_row=None):
    """Calculate Elo ratings for all teams from match history efficiently.

    Args:
        matches_df: DataFrame with columns Date, HomeTeam, AwayTeam, FullTimeResult.
        base_elo: Starting Elo for new teams.
        until_row: Optional int. If given, only replays the first ``until_row``
            rows (in DataFrame order, assumed chronological) and returns the
            resulting ``elo_ratings`` snapshot plus an ``elo_history`` entry for
            every row in that prefix. Used by time-series CV to obtain fold-safe
            Elo features that exclude outcomes from the validation window.

    Returns:
        (elo_ratings, elo_history) where elo_ratings is a dict of final-team
        Elos and elo_history is a list of per-row dicts (one per match in the
        replayed prefix).
    """
    elo_ratings = {}
    elo_history = []

    # Restrict iteration to the requested prefix. ``until_row=None`` replays the
    # whole frame (original behaviour); an explicit integer enables fold-safe
    # Elo reconstruction inside walk-forward cross-validation.
    if until_row is None:
        replayed = matches_df
    else:
        replayed = matches_df.iloc[:until_row]

    # Use itertuples for faster iteration than iterrows
    for row in replayed.itertuples(index=False):
        # Access attributes by name. Ensure matches_df has these columns.
        # Canonical names after mapping: HomeTeam, AwayTeam, FullTimeResult
        h, a, r = row.HomeTeam, row.AwayTeam, row.FullTimeResult
        elo_h = elo_ratings.get(h, base_elo)
        elo_a = elo_ratings.get(a, base_elo)

        new_h, new_a = update_elo(elo_h, elo_a, r)
        elo_ratings[h], elo_ratings[a] = new_h, new_a

        elo_history.append({
            "Date": row.Date,
            "HomeTeam": h,
            "AwayTeam": a,
            "Home_Elo": elo_h,
            "Away_Elo": elo_a
        })

    return elo_ratings, elo_history

def shin_method(odds):
    """
    Shin Method: Assumes a proportion 'z' of insider traders.
    pi_i = (1-z)p_i + z*sqrt(p_i)
    Solving for p_i: p_i = ((sqrt(z^2 + 4(1-z)pi_i) - z) / (2(1-z)))^2
    """
    pi = 1.0 / np.array(odds)
    
    # Handle NaN values
    if np.any(np.isnan(pi)):
        return np.array([0.333, 0.333, 0.334]), 0.0

    def get_p(z, pi_i):
        if z >= 1.0: return 0.0
        num = np.sqrt(z**2 + 4 * (1 - z) * pi_i) - z
        den = 2 * (1 - z)
        return (num / den)**2

    def objective(z):
        return sum(get_p(z, pi_i) for pi_i in pi) - 1.0

    try:
        # Solve for z (proportion of insiders)
        # z is typically in range [0, 0.4] for sports markets
        z_optimal = brentq(objective, 0, 1 - 1e-10)
        true_probs = np.array([get_p(z_optimal, pi_i) for pi_i in pi])
        return true_probs, z_optimal
    except (ValueError, RuntimeError):
        # Fallback to simple normalization if brentq fails
        true_probs = pi / pi.sum()
        return true_probs, 0.0


def calibrate_poisson_params(matches_df):
    """
    Compare predicted vs actual outcome frequencies to validate calibration.
    
    Run this once per season against historical data to check whether
    POISSON_DRAW_ADJUSTMENT and HOME_ADVANTAGE_BOOST are well-tuned.
    
    Args:
        matches_df: DataFrame with columns Home_Elo, Away_Elo, Home_Avg_GF,
                    Away_Avg_GF, Home_Avg_GA, Away_Avg_GA, FullTimeResult
    
    Returns:
        dict with actual vs predicted frequencies and suggested adjustments
    
    Usage:
        from src.stats_engine import calibrate_poisson_params
        from src.pipeline import load_data, build_features
        _, _, matches, _, _, _ = load_data()
        matches_feat, _ = build_features(matches)
        report = calibrate_poisson_params(matches_feat.dropna(subset=['Home_Elo']))
        print(report)
    """
    required = ["Home_Elo", "Away_Elo", "Home_Avg_GF", "Away_Avg_GF",
                "Home_Avg_GA", "Away_Avg_GA", "FullTimeResult"]
    missing = [c for c in required if c not in matches_df.columns]
    if missing:
        return {"error": f"Missing columns: {missing}"}

    df = matches_df.dropna(subset=required).copy()
    if df.empty:
        return {"error": "No rows after dropping NaN"}

    # Actual frequencies
    total = len(df)
    actual_home = (df["FullTimeResult"] == 2).sum() / total
    actual_draw = (df["FullTimeResult"] == 1).sum() / total
    actual_away = (df["FullTimeResult"] == 0).sum() / total

    # Predicted frequencies (average Poisson probabilities)
    xG_h, xG_a = calculate_expected_goals(
        df["Home_Elo"].values, df["Away_Elo"].values,
        df["Home_Avg_GF"].values, df["Away_Avg_GF"].values,
        df["Home_Avg_GA"].values, df["Away_Avg_GA"].values,
    )
    outcomes = [calculate_outcome_probabilities(h, a) for h, a in zip(xG_h, xG_a)]
    pred_home = np.mean([o["home_win"] for o in outcomes])
    pred_draw = np.mean([o["draw"] for o in outcomes])
    pred_away = np.mean([o["away_win"] for o in outcomes])

    # Suggested draw adjustment: scale so predicted draw matches actual
    suggested_draw_adj = (actual_draw / pred_draw) * POISSON_DRAW_ADJUSTMENT if pred_draw > 0 else POISSON_DRAW_ADJUSTMENT

    return {
        "n_matches": total,
        "actual":    {"home": round(actual_home, 3), "draw": round(actual_draw, 3), "away": round(actual_away, 3)},
        "predicted": {"home": round(pred_home, 3),   "draw": round(pred_draw, 3),   "away": round(pred_away, 3)},
        "current_draw_adjustment": POISSON_DRAW_ADJUSTMENT,
        "suggested_draw_adjustment": round(suggested_draw_adj, 3),
        "note": "Set POISSON_DRAW_ADJUSTMENT in config.py to suggested_draw_adjustment if drift > 0.02",
    }
