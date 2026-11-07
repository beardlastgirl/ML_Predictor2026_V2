"""
bivariate_predictor.py
Robust Argentine Football Prediction Engine:
- Dixon-Coles Bivariate Poisson Modeling with Low-Score Correlation
- Margin-of-Victory (MOV) Scaled Elo Ratings with Seasonal Mean-Reversion
- Gradient Boosting Stacking Layer
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import factorial
from typing import Dict, Tuple, List, Optional


class DynamicArgentineElo:
    """Elo engine tailored for Argentine domestic volatility."""

    def __init__(
        self,
        base_elo: float = 1500.0,
        k_base: float = 24.0,
        home_advantage: float = 65.0,
        reversion_rate: float = 0.20,
    ):
        self.base_elo = base_elo
        self.k_base = k_base
        self.home_advantage = home_advantage
        self.reversion_rate = reversion_rate
        self.ratings: Dict[str, float] = {}

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.base_elo)

    def apply_season_transition(self):
        """Soft-reset ratings toward league mean at tournament/season transitions."""
        for team in self.ratings:
            self.ratings[team] = (
                (1.0 - self.reversion_rate) * self.ratings[team]
                + self.reversion_rate * self.base_elo
            )

    def update(
        self, home: str, away: str, home_goals: int, away_goals: int
    ) -> Tuple[float, float, float, float]:
        r_h = self.get_rating(home)
        r_a = self.get_rating(away)

        # Expected score with home field advantage
        exp_h = 1.0 / (1.0 + 10.0 ** ((r_a - (r_h + self.home_advantage)) / 400.0))
        exp_a = 1.0 - exp_h

        # Actual score
        if home_goals > away_goals:
            s_h, s_a = 1.0, 0.0
        elif home_goals == away_goals:
            s_h, s_a = 0.5, 0.5
        else:
            s_h, s_a = 0.0, 1.0

        # Margin of Victory (MOV) multiplier to capture goal dominance
        goal_diff = abs(home_goals - away_goals)
        if goal_diff <= 1:
            mov_mult = 1.0
        elif goal_diff == 2:
            mov_mult = 1.5
        else:
            mov_mult = (11.0 + goal_diff) / 8.0

        # Autocorrelation dampening for high-rated matchups
        elo_diff = abs((r_h + self.home_advantage) - r_a)
        damping = 2.2 / ((elo_diff * 0.001) + 2.2)
        k_eff = self.k_base * mov_mult * damping

        # Update and persist
        new_r_h = np.clip(r_h + k_eff * (s_h - exp_h), 800.0, 2400.0)
        new_r_a = np.clip(r_a + k_eff * (s_a - exp_a), 800.0, 2400.0)

        self.ratings[home] = float(new_r_h)
        self.ratings[away] = float(new_r_a)
        return r_h, r_a, float(new_r_h), float(new_r_a)


class DixonColesGoalModel:
    """
    Bivariate goal model via Dixon-Coles formulation.
    Models marginal Poisson intensities (lambda, mu) while applying
    correction factor tau to capture draw inflation in low-scoring games.
    """

    def __init__(self, max_goals: int = 8):
        self.max_goals = max_goals
        self.rho = -0.06  # Low-score correlation parameter for Argentine league

    @staticmethod
    def _tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
        """Dixon-Coles adjustment factor for score combinations {0, 1} x {0, 1}."""
        if x == 0 and y == 0:
            return 1.0 - (lam * mu * rho)
        elif x == 0 and y == 1:
            return 1.0 + (lam * rho)
        elif x == 1 and y == 0:
            return 1.0 + (mu * rho)
        elif x == 1 and y == 1:
            return 1.0 - rho
        return 1.0

    def fit_rho(self, actual_scores: List[Tuple[int, int]], expected_xg: List[Tuple[float, float]]):
        """Fit empirical rho via negative log-likelihood on training folds."""
        def nll(params):
            r = params[0]
            log_lik = 0.0
            for (x, y), (lam, mu) in zip(actual_scores, expected_xg):
                if lam <= 0 or mu <= 0:
                    continue
                p_indep = (np.exp(-lam) * (lam ** x) / factorial(x)) * (
                    np.exp(-mu) * (mu ** y) / factorial(y)
                )
                adj = self._tau(x, y, lam, mu, r)
                prob = max(1e-12, p_indep * adj)
                log_lik += np.log(prob)
            return -log_lik

        res = minimize(nll, x0=[self.rho], bounds=[(-0.25, 0.25)], method="L-BFGS-B")
        if res.success:
            self.rho = float(res.x[0])

    def predict_match_distribution(
        self, lambda_home: float, lambda_away: float
    ) -> Dict[str, float]:
        """Generate scoreline grid and exact outcome probabilities."""
        lam = max(0.1, float(lambda_home))
        mu = max(0.1, float(lambda_away))

        goals = np.arange(self.max_goals + 1)
        p_h = np.exp(-lam) * (lam ** goals) / factorial(goals)
        p_a = np.exp(-mu) * (mu ** goals) / factorial(goals)

        # Joint probability matrix with tau correction
        grid = np.outer(p_h, p_a)
        for x in [0, 1]:
            for y in [0, 1]:
                grid[x, y] *= self._tau(x, y, lam, mu, self.rho)

        # Normalize grid to resolve truncation
        grid = np.maximum(0.0, grid)
        grid_sum = grid.sum()
        if grid_sum > 0:
            grid /= grid_sum

        # Partition probabilities across outcome triangles
        h_idx, a_idx = np.indices((self.max_goals + 1, self.max_goals + 1))
        p_home_win = float(grid[h_idx > a_idx].sum())
        p_draw = float(grid[h_idx == a_idx].sum())
        p_away_win = float(grid[h_idx < a_idx].sum())

        return {
            "p_home": p_home_win,
            "p_draw": p_draw,
            "p_away": p_away_win,
            "expected_h_goals": float((h_idx * grid).sum()),
            "expected_a_goals": float((a_idx * grid).sum()),
            "score_matrix": grid,
        }


class HybridMatchPredictor:
    """
    End-to-end inference wrapper integrating Dynamic Elo, venue-split stats,
    and the Dixon-Coles engine into gradient-boosted features.
    """

    def __init__(self, elo_engine: DynamicArgentineElo, goal_engine: DixonColesGoalModel):
        self.elo = elo_engine
        self.goals = goal_engine

    def build_bivariate_features(
        self,
        home_team: str,
        away_team: str,
        home_venue_gf: float,
        home_venue_ga: float,
        away_venue_gf: float,
        away_venue_ga: float,
        travel_distance_km: float = 0.0,
    ) -> Dict[str, float]:
        h_elo = self.elo.get_rating(home_team)
        a_elo = self.elo.get_rating(away_team)
        elo_diff = (h_elo + self.elo.home_advantage) - a_elo

        # Distance-decay tax on away scoring and stamina (AMBA vs Interior penalty)
        travel_penalty = np.clip(travel_distance_km / 1500.0 * 0.08, 0.0, 0.15)

        # Venue-split attack vs defense intensities
        lam_h = np.exp(
            0.15 + (0.0012 * elo_diff) + (0.45 * np.log(max(0.2, home_venue_gf))) +
            (0.35 * np.log(max(0.2, away_venue_ga)))
        )
        lam_a = np.exp(
            -0.10 - (0.0012 * elo_diff) + (0.45 * np.log(max(0.2, away_venue_gf))) +
            (0.35 * np.log(max(0.2, home_venue_ga))) - travel_penalty
        )

        bivariate_out = self.goals.predict_match_distribution(lam_h, lam_a)

        return {
            "Home_Elo": h_elo,
            "Away_Elo": a_elo,
            "Elo_Diff": elo_diff,
            "Travel_Penalty": travel_penalty,
            "Lambda_Home": lam_h,
            "Lambda_Away": lam_a,
            "Bivariate_P_Home": bivariate_out["p_home"],
            "Bivariate_P_Draw": bivariate_out["p_draw"],
            "Bivariate_P_Away": bivariate_out["p_away"],
            "Expected_Home_Goals": bivariate_out["expected_h_goals"],
            "Expected_Away_Goals": bivariate_out["expected_a_goals"],
        }
