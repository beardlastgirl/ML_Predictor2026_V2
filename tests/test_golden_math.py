"""
Golden Math Regression Suite - ML_Predictor2026_V2

This test suite freezes exact numerical snapshots for core mathematical functions.
Any change to these values indicates a regression or intentional modification.

Run with: python -m pytest tests/test_golden_math.py -v
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stats_engine import (
    expected_result,
    update_elo,
    calculate_expected_goals,
    poisson_probability,
    calculate_outcome_probabilities,
    calculate_poisson_features,
    calculate_all_elo_ratings,
    shin_method,
)
from src.config import (
    BASE_ELO, K_FACTOR, HOME_ADVANTAGE, BASE_GOAL_RATE, MAX_GOALS,
    POISSON_DRAW_ADJUSTMENT, HOME_ADVANTAGE_BOOST, ML_POISSON_BLEND_RATIO
)


class TestGoldenElo:
    """Golden tests for Elo calculations."""

    def test_expected_result_golden(self):
        """Expected result for equal teams."""
        result = expected_result(1500, 1500)
        assert result == pytest.approx(0.5, abs=1e-10)

    def test_expected_result_elo_diff_golden(self):
        """Expected result for 100 Elo difference."""
        result = expected_result(1600, 1500)
        # ELO_DIVISOR = 400
        expected = 1 / (1 + 10 ** ((1500 - 1600) / 400))
        assert result == pytest.approx(expected, abs=1e-10)

    def test_update_elo_home_win_golden(self):
        """Elo update for home win with equal teams."""
        home_elo, away_elo = 1500, 1500
        new_home, new_away = update_elo(home_elo, away_elo, 2)

        # exp_home = 1 / (1 + 10^((1500 - 1500 - 65)/400)) = 1 / (1 + 10^(-65/400))
        # exp_home = 1 / (1 + 10^(-0.1625)) = 1 / (1 + 0.688) = 0.592
        # home_elo_new = 1500 + 30 * (1 - 0.592) = 1500 + 30 * 0.408 = 1512.24
        # away_elo_new = 1500 + 30 * (0 - 0.408) = 1500 - 12.24 = 1487.76
        exp_home = 1 / (1 + 10 ** ((away_elo - (home_elo + HOME_ADVANTAGE)) / 400))
        expected_home = home_elo + K_FACTOR * (1 - exp_home)
        expected_away = away_elo + K_FACTOR * (0 - (1 - exp_home))

        assert new_home == pytest.approx(expected_home, abs=1e-10)
        assert new_away == pytest.approx(expected_away, abs=1e-10)

    def test_update_elo_draw_golden(self):
        """Elo update for draw with equal teams."""
        home_elo, away_elo = 1500, 1500
        new_home, new_away = update_elo(home_elo, away_elo, 1)

        exp_home = 1 / (1 + 10 ** ((away_elo - (home_elo + HOME_ADVANTAGE)) / 400))
        expected_home = home_elo + K_FACTOR * (0.5 - exp_home)
        expected_away = away_elo + K_FACTOR * (0.5 - (1 - exp_home))

        assert new_home == pytest.approx(expected_home, abs=1e-10)
        assert new_away == pytest.approx(expected_away, abs=1e-10)

    def test_update_elo_away_win_golden(self):
        """Elo update for away win with equal teams."""
        home_elo, away_elo = 1500, 1500
        new_home, new_away = update_elo(home_elo, away_elo, 0)

        exp_home = 1 / (1 + 10 ** ((away_elo - (home_elo + HOME_ADVANTAGE)) / 400))
        expected_home = home_elo + K_FACTOR * (0 - exp_home)
        expected_away = away_elo + K_FACTOR * (1 - (1 - exp_home))

        assert new_home == pytest.approx(expected_home, abs=1e-10)
        assert new_away == pytest.approx(expected_away, abs=1e-10)


class TestGoldenPoisson:
    """Golden tests for Poisson calculations."""

    def test_poisson_probability_golden(self):
        """Poisson PMF at lambda=1.5 for k=1."""
        result = poisson_probability(1, 1.5)
        # scipy.stats.poisson.pmf(1, 1.5)
        expected = 0.3346952401873944
        assert result == pytest.approx(expected, abs=1e-10)

    def test_poisson_sum_golden(self):
        """Poisson sum to 1."""
        total = sum(poisson_probability(k, 1.5) for k in range(50))
        assert total == pytest.approx(1.0, abs=1e-10)


class TestGoldenExpectedGoals:
    """Golden tests for expected goals calculations."""

    def test_calculate_expected_goals_equal_golden(self):
        """Expected goals for equal teams."""
        xG_home, xG_away = calculate_expected_goals(
            elo_home=1500, elo_away=1500,
            avg_gf_home=1.3, avg_gf_away=1.3,
            avg_ga_home=1.0, avg_ga_away=1.0
        )

        # GOAL_WEIGHT_ATTACK=0.55, GOAL_WEIGHT_DEFENSE=0.45, HOME_BOOST=1.15
        # xG_home = (0.55 * 1.3 + 0.45 * 1.0) * 1.15 = 1.165 * 1.15 = 1.33975
        # xG_away = 0.55 * 1.3 + 0.45 * 1.0 = 1.165
        # elo_diff = 0, elo_factor = 1 + 0/5000 = 1

        expected_home = (0.55 * 1.3 + 0.45 * 1.0) * 1.15
        expected_away = 0.55 * 1.3 + 0.45 * 1.0

        assert xG_home == pytest.approx(expected_home, abs=1e-10)
        assert xG_away == pytest.approx(expected_away, abs=1e-10)

    def test_calculate_expected_goals_with_elo_diff_golden(self):
        """Expected goals with Elo difference."""
        xG_home, xG_away = calculate_expected_goals(
            elo_home=1600, elo_away=1400,
            avg_gf_home=1.3, avg_gf_away=1.3,
            avg_ga_home=1.0, avg_ga_away=1.0
        )

        base_home = (0.55 * 1.3 + 0.45 * 1.0) * 1.15
        base_away = 0.55 * 1.3 + 0.45 * 1.0
        elo_diff = 200
        elo_factor = 1 + (elo_diff / 5000)  # 1 + 200/5000 = 1.04

        expected_home = base_home * elo_factor
        expected_away = base_away / elo_factor

        assert xG_home == pytest.approx(expected_home, abs=1e-10)
        assert xG_away == pytest.approx(expected_away, abs=1e-10)


class TestGoldenOutcomeProbabilities:
    """Golden tests for outcome probabilities."""

    def test_calculate_outcome_probabilities_golden(self):
        """Outcome probabilities for typical match."""
        outcomes = calculate_outcome_probabilities(1.5, 1.2)

        # Exact calculated values for xG_home=1.5, xG_away=1.2
        # With MAX_GOALS=8, POISSON_DRAW_ADJUSTMENT=1.11, HOME_ADVANTAGE_BOOST=0.02
        assert outcomes['home_win'] == pytest.approx(0.4404416046877295, abs=1e-10)
        assert outcomes['draw'] == pytest.approx(0.2800552896584424, abs=1e-10)
        assert outcomes['away_win'] == pytest.approx(0.2795031056538281, abs=1e-10)

    def test_calculate_outcome_probabilities_sum_golden(self):
        """Probabilities sum to 1."""
        outcomes = calculate_outcome_probabilities(1.5, 1.2)
        total = outcomes['home_win'] + outcomes['draw'] + outcomes['away_win']
        assert total == pytest.approx(1.0, abs=1e-10)


class TestGoldenPoissonFeatures:
    """Golden tests for full Poisson feature calculation."""

    def test_calculate_poisson_features_golden(self):
        """Full Poisson feature set."""
        features = calculate_poisson_features(
            elo_home=1500, elo_away=1500,
            avg_gf_home=1.3, avg_gf_away=1.3,
            avg_ga_home=1.0, avg_ga_away=1.0
        )

        assert features['xG_home'] == pytest.approx(1.33975, abs=1e-10)
        assert features['xG_away'] == pytest.approx(1.165, abs=1e-10)
        assert features['xG_diff'] == pytest.approx(0.17475, abs=1e-10)

        # Matches calibrated outcome probabilities
        assert features['Poisson_Home_Win'] == pytest.approx(0.4067938056455006, abs=1e-10)
        assert features['Poisson_Draw'] == pytest.approx(0.29507625648770097, abs=1e-10)
        assert features['Poisson_Away_Win'] == pytest.approx(0.2981299378667985, abs=1e-10)

        # Expected goals match the xG values after Poisson grid computation
        assert features['Expected_Home_Goals'] == pytest.approx(1.3396596657675306, abs=1e-10)
        assert features['Expected_Away_Goals'] == pytest.approx(1.1649694183156658, abs=1e-10)
        assert features['Expected_Total_Goals'] == pytest.approx(2.5046290840831964, abs=1e-10)


class TestGoldenShinMethod:
    """Golden tests for Shin method."""

    def test_shin_method_golden(self):
        """Shin method with typical odds."""
        odds = [2.0, 3.2, 3.6]  # Home, Draw, Away
        probs, z = shin_method(odds)

        # Verify probabilities sum to 1
        assert sum(probs) == pytest.approx(1.0, abs=1e-10)
        # Verify z is in valid range
        assert 0 <= z < 1
        # Home win should be highest probability (lowest odds)
        assert probs[0] > probs[1]
        assert probs[0] > probs[2]

    def test_shin_method_equal_odds_golden(self):
        """Shin method with equal odds."""
        odds = [3.0, 3.0, 3.0]
        probs, z = shin_method(odds)

        # With equal odds, should get equal probabilities
        assert probs[0] == pytest.approx(1/3, abs=1e-10)
        assert probs[1] == pytest.approx(1/3, abs=1e-10)
        assert probs[2] == pytest.approx(1/3, abs=1e-10)

    def test_shin_method_nan_golden(self):
        """Shin method with NaN values returns uniform."""
        odds = [np.nan, 3.2, 3.6]
        probs, z = shin_method(odds)

        # Fallback returns 1/3 for each outcome (0.333, 0.333, 0.334)
        assert probs[0] == pytest.approx(0.333, abs=1e-3)
        assert probs[1] == pytest.approx(0.333, abs=1e-3)
        assert probs[2] == pytest.approx(0.334, abs=1e-3)
        assert 0 <= z < 1


class TestGoldenEloHistory:
    """Golden tests for Elo history calculation."""

    def test_calculate_all_elo_ratings_golden(self):
        """Full Elo history for known match sequence."""
        import pandas as pd

        matches = pd.DataFrame({
            'Date': pd.to_datetime(['2024-01-01', '2024-01-08', '2024-01-15']),
            'Home': ['TeamA', 'TeamB', 'TeamA'],
            'Away': ['TeamB', 'TeamA', 'TeamB'],
            'Res': [2, 0, 2],  # Home win, Away win, Home win
        })

        elo_ratings, elo_history = calculate_all_elo_ratings(matches, BASE_ELO)

        # After 3 matches:
        # Match 1: TeamA (home) beats TeamB -> A gains, B loses
        # Match 2: TeamA (away) beats TeamB -> A gains more, B loses more
        # Match 3: TeamA (home) beats TeamB -> A gains, B loses

        # TeamA: starts 1500, after M1 (home win): ~1512, after M2 (away win): ~1524, after M3 (home win): ~1536
        # TeamB: starts 1500, after M1 (away loss): ~1488, after M2 (home loss): ~1476, after M3 (away loss): ~1464

        assert 'TeamA' in elo_ratings
        assert 'TeamB' in elo_ratings
        assert elo_ratings['TeamA'] > elo_ratings['TeamB']
        assert len(elo_history) == 3


class TestGoldenConfig:
    """Verify config constants haven't drifted."""

    def test_config_constants_golden(self):
        """Critical config values match expected."""
        assert BASE_ELO == 1500
        assert K_FACTOR == 30
        assert HOME_ADVANTAGE == 65
        assert BASE_GOAL_RATE == 1.11
        assert MAX_GOALS == 8
        assert POISSON_DRAW_ADJUSTMENT == 1.11
        assert HOME_ADVANTAGE_BOOST == 0.02
        assert ML_POISSON_BLEND_RATIO == 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])