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
    """Calculate expected goals for each team."""
    league_avg = BASE_GOAL_RATE
    avg_gf_home = avg_gf_home if pd.notna(avg_gf_home) else league_avg
    avg_gf_away = avg_gf_away if pd.notna(avg_gf_away) else league_avg
    avg_ga_home = avg_ga_home if pd.notna(avg_ga_home) else league_avg
    avg_ga_away = avg_ga_away if pd.notna(avg_ga_away) else league_avg

    xG_home = (GOAL_WEIGHT_ATTACK * avg_gf_home + GOAL_WEIGHT_DEFENSE * avg_ga_away) * HOME_BOOST
    xG_away = GOAL_WEIGHT_ATTACK * avg_gf_away + GOAL_WEIGHT_DEFENSE * avg_ga_home

    elo_diff = elo_home - elo_away
    elo_factor = 1 + (elo_diff / ELO_FACTOR_DENOM)

    xG_home = xG_home * elo_factor
    xG_away = xG_away / elo_factor

    xG_home = max(XG_MIN, min(XG_MAX, xG_home))
    xG_away = max(XG_MIN, min(XG_MAX, xG_away))

    return xG_home, xG_away

def poisson_probability(goals, expected):
    """Calculate Poisson probability of scoring exactly k goals."""
    return poisson.pmf(goals, expected)

def calculate_outcome_probabilities(xG_home, xG_away, max_goals=MAX_GOALS):
    """Calculate match outcome probabilities from Poisson goal distributions.

    Applies calibration adjustment to reduce draw bias toward league averages.
    Liga Profesional typical: ~45% Home, ~33% Draw, ~22% Away
    
    DRAW CALIBRATION APPLIED HERE:
    This is the PRIMARY stage for draw calibration. The calculation:
    1. Generates Poisson grid of all possible scorelines
    2. Sums probabilities for each outcome: H/D/A
    3. Applies POISSON_DRAW_ADJUSTMENT to reduce raw Poisson draws
    4. Applies HOME_ADVANTAGE_BOOST to increase home win probability
    
    NOTE: This function ONLY calibrates Poisson probabilities.
    The model prediction also applies ML ensemble blending (60/40) in model_engine.py,
    which further refines the probabilities using trained ML model.
    
    DO NOT modify this logic without updating:
    - config.py POISSON_DRAW_ADJUSTMENT documentation
    - model_engine.py ensemble blending (line 115)
    - tests/test_main.py calibration tests
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

    # Calibrate probabilities toward league averages
    # Reduce draw probability, redistribute to home/away based on xG
    p_draw_calibrated = p_draw * POISSON_DRAW_ADJUSTMENT
    remainder = 1.0 - p_draw_calibrated

    # Redistribute the remainder proportionally to home/away win probabilities
    total_win = p_home_win + p_away_win
    if total_win > 0:
        p_home_win = (p_home_win / total_win) * remainder
        p_away_win = (p_away_win / total_win) * remainder
    else:
        # Edge case: split evenly if both are zero
        p_home_win = remainder / 2
        p_away_win = remainder / 2

    # Add home advantage boost to final probability
    # This reflects the ~45% home win rate in Liga Profesional
    home_advantage_boost = 0.08  # ~8% boost to home win probability
    p_home_win = min(0.95, p_home_win + home_advantage_boost)
    p_away_win = max(0.05, p_away_win - home_advantage_boost * 0.5)

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

def calculate_all_elo_ratings(matches_df, base_elo=BASE_ELO):
    """Calculate Elo ratings for all teams from match history.

    Args:
        matches_df: DataFrame with Home, Away, Res columns (Res = 0/1/2)
        base_elo: Starting Elo for new teams

    Returns:
        tuple: (elo_ratings dict, elo_history list of dicts)
    """
    elo_ratings = {}
    elo_history = []

    for _, row in matches_df.iterrows():
        h, a, r = row["Home"], row["Away"], row["Res"]
        elo_h = elo_ratings.get(h, base_elo)
        elo_a = elo_ratings.get(a, base_elo)
        new_h, new_a = update_elo(elo_h, elo_a, r)
        elo_ratings[h], elo_ratings[a] = new_h, new_a
        elo_history.append({
            "Date": row["Date"],
            "Home": h,
            "Away": a,
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
