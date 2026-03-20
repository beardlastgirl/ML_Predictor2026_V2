"""
Test suite for ML_Predictor2026_V2 main.py

Tests core functions including:
- Poisson distribution calculations
- Expected goals calculations
- Outcome probability calculations
- Team name normalization
- Elo calculations
- Feature engineering
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions to test
from src.data_processing import normalize_team_name, load_glossary
from src.stats_engine import (
    expected_result,
    update_elo,
    calculate_expected_goals,
    poisson_probability,
    calculate_outcome_probabilities,
    calculate_poisson_features,
)
from src.features import get_team_trailing_stats, compute_trailing_features
from src.config import BASE_ELO, K_FACTOR, HOME_ADVANTAGE, BASE_GOAL_RATE, MAX_GOALS


# ==============================================
# Test Team Name Normalization
# ==============================================

def test_normalize_team_name_basic():
    """Test basic team name normalization."""
    assert normalize_team_name("boca juniors") == "BOCA JUNIORS"
    assert normalize_team_name("River Plate") == "RIVER PLATE"


def test_normalize_team_name_with_glossary():
    """Test team name normalization with glossary."""
    glossary = {"BOCA": "BOCA JUNIORS"}
    assert normalize_team_name("Boca", glossary) == "BOCA JUNIORS"


def test_normalize_team_name_special_chars():
    """Test handling of special characters."""
    assert normalize_team_name("San Lorenzo") == "SAN LORENZO"
    assert normalize_team_name("Velez Sarsfield") == "VELEZ SARSFIELD"


# ==============================================
# Test Elo Calculations
# ==============================================

def test_expected_result():
    """Test expected result calculation."""
    # Equal teams should have 0.5 expected score
    assert expected_result(1500, 1500) == pytest.approx(0.5, abs=0.01)

    # Stronger team should have higher expected score
    assert expected_result(1600, 1500) > 0.5
    assert expected_result(1500, 1600) < 0.5


def test_elo_update_home_win():
    """Test Elo update for home win."""
    home_elo, away_elo = 1500, 1500
    # Home win = 2
    new_home, new_away = update_elo(home_elo, away_elo, 2)

    assert new_home > home_elo  # Home gains points
    assert new_away < away_elo  # Away loses points


def test_elo_update_away_win():
    """Test Elo update for away win."""
    home_elo, away_elo = 1500, 1500
    # Away win = 0
    new_home, new_away = update_elo(home_elo, away_elo, 0)

    assert new_home < home_elo  # Home loses points
    assert new_away > away_elo  # Away gains points


def test_elo_update_draw():
    """Test Elo update for draw."""
    home_elo, away_elo = 1500, 1500
    # Draw = 1
    new_home, new_away = update_elo(home_elo, away_elo, 1)

    # Both should be close to original (small change for draw)
    assert abs(new_home - home_elo) < 5
    assert abs(new_away - away_elo) < 5


def test_elo_home_advantage():
    """Test that home advantage is applied."""
    # Home team with same Elo should be favored
    home_elo, away_elo = 1500, 1500
    exp_result = expected_result(home_elo + HOME_ADVANTAGE, away_elo)

    assert exp_result > 0.5  # Home team is favored


# ==============================================
# Test Poisson Distribution Functions
# ==============================================

def test_poisson_probability_sum():
    """Test that Poisson probabilities sum to approximately 1."""
    total_prob = sum(poisson_probability(k, 1.5) for k in range(20))
    assert total_prob == pytest.approx(1.0, abs=0.001)


def test_poisson_probability_peak():
    """Test that most likely goals equals floor of expected."""
    # For lambda = 1.5, most likely is 1 goal
    assert poisson_probability(1, 1.5) > poisson_probability(0, 1.5)
    assert poisson_probability(1, 1.5) > poisson_probability(2, 1.5)


def test_calculate_expected_goals_basic():
    """Test basic expected goals calculation."""
    xG_home, xG_away = calculate_expected_goals(
        elo_home=1500, elo_away=1500,
        avg_gf_home=1.3, avg_gf_away=1.3,
        avg_ga_home=1.0, avg_ga_away=1.0
    )

    # Should be reasonable based on the provided stats
    assert xG_home > 1.0  # Reasonable expected value based on stats
    assert xG_away < xG_home  # Home scores more


def test_calculate_expected_goals_strong_attack():
    """Test expected goals with strong attack."""
    xG_home, xG_away = calculate_expected_goals(
        elo_home=1600, elo_away=1400,
        avg_gf_home=2.0, avg_gf_away=0.5,
        avg_ga_home=0.5, avg_ga_away=2.0
    )

    # Strong home team should have high xG
    assert xG_home > 2.0
    # Weak away team should have low xG against
    assert xG_away < 1.0


def test_calculate_expected_goals_bounds():
    """Test that xG values stay within reasonable bounds."""
    for _ in range(10):
        xG_home, xG_away = calculate_expected_goals(
            elo_home=np.random.randint(1300, 1700),
            elo_away=np.random.randint(1300, 1700),
            avg_gf_home=np.random.uniform(0.5, 3.0),
            avg_gf_away=np.random.uniform(0.5, 3.0),
            avg_ga_home=np.random.uniform(0.5, 3.0),
            avg_ga_away=np.random.uniform(0.5, 3.0)
        )

        assert 0.2 <= xG_home <= 4.0
        assert 0.2 <= xG_away <= 4.0


def test_calculate_outcome_probabilities_sum():
    """Test that outcome probabilities sum to 1."""
    outcomes = calculate_outcome_probabilities(1.5, 1.2)

    total = outcomes['home_win'] + outcomes['draw'] + outcomes['away_win']
    assert total == pytest.approx(1.0, abs=0.001)


def test_calculate_outcome_probabilities_strong_home():
    """Test that strong home team has higher win probability."""
    # Strong home, weak away
    outcomes_home = calculate_outcome_probabilities(2.0, 0.8)
    # Weak home, strong away
    outcomes_away = calculate_outcome_probabilities(0.8, 2.0)

    assert outcomes_home['home_win'] > outcomes_away['home_win']
    assert outcomes_away['away_win'] > outcomes_home['away_win']


def test_calculate_outcome_probabilities_draw():
    """Test equal teams should have higher draw probability."""
    outcomes = calculate_outcome_probabilities(1.3, 1.3)

    # Equal teams should have ~25-35% draw (rest split between wins)
    assert 0.20 < outcomes['draw'] < 0.45


def test_calculate_outcome_probabilities_expected_goals():
    """Test that expected goals match calculated values."""
    outcomes = calculate_outcome_probabilities(1.5, 1.2)

    assert outcomes['expected_home_goals'] == pytest.approx(1.5, abs=0.01)
    assert outcomes['expected_away_goals'] == pytest.approx(1.2, abs=0.01)


def test_calculate_poisson_features():
    """Test full Poisson feature calculation."""
    features = calculate_poisson_features(
        elo_home=1500, elo_away=1500,
        avg_gf_home=1.3, avg_gf_away=1.3,
        avg_ga_home=1.0, avg_ga_away=1.0
    )

    assert 'xG_home' in features
    assert 'xG_away' in features
    assert 'xG_diff' in features
    assert 'Poisson_Home_Win' in features
    assert 'Poisson_Draw' in features
    assert 'Poisson_Away_Win' in features
    assert 'Expected_Home_Goals' in features
    assert 'Expected_Away_Goals' in features

    # Check bounds
    assert 0 <= features['Poisson_Home_Win'] <= 1
    assert 0 <= features['Poisson_Draw'] <= 1
    assert 0 <= features['Poisson_Away_Win'] <= 1


def test_calculate_poisson_features_ml_enhancement():
    """Test Poisson features can be used as ML features."""
    # Strong home, weak away
    features = calculate_poisson_features(
        elo_home=1600, elo_away=1400,
        avg_gf_home=2.0, avg_gf_away=0.5,
        avg_ga_home=0.5, avg_ga_away=2.0
    )

    # Should have high home win probability
    assert features['Poisson_Home_Win'] > 0.5
    assert features['xG_home'] > features['xG_away']


# ==============================================
# Test Trailing Features
# ==============================================

def test_get_team_trailing_stats_empty():
    """Test trailing stats with no history."""
    stats = get_team_trailing_stats([], 8)

    assert stats['avg_gf'] is np.nan
    assert stats['avg_ga'] is np.nan
    assert stats['matches'] == 0


def test_get_team_trailing_stats_single_match():
    """Test trailing stats with single match."""
    history = [{'gf': 2, 'ga': 1, 'is_home': True}]
    stats = get_team_trailing_stats(history, 8)

    assert stats['avg_gf'] == 2
    assert stats['avg_ga'] == 1
    assert stats['avg_gd'] == 1
    assert stats['matches'] == 1


def test_get_team_trailing_stats_form_win():
    """Test form calculation with wins."""
    history = [
        {'gf': 2, 'ga': 1},  # Win
        {'gf': 1, 'ga': 0},  # Win
        {'gf': 0, 'ga': 0},  # Draw
    ]
    # 2 wins + 1 draw = 7 points / 3 games = 2.33
    stats = get_team_trailing_stats(history, 8)

    assert stats['form'] == pytest.approx(7/3, abs=0.01)


def test_get_team_trailing_stats_window_limit():
    """Test that trailing window limits matches considered."""
    history = [
        {'gf': 3, 'ga': 0},
        {'gf': 2, 'ga': 1},
        {'gf': 1, 'ga': 0},
        {'gf': 0, 'ga': 0},
    ]
    # Window of 3 should only consider last 3 matches
    stats = get_team_trailing_stats(history, 3)

    assert stats['matches'] == 3
    assert stats['avg_gf'] == pytest.approx((2+1+0)/3, abs=0.01)


def test_compute_trailing_features_basic():
    """Test computing trailing features for a small dataset."""
    matches = pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-08', '2024-01-15']),
        'Home': ['TeamA', 'TeamB', 'TeamA'],
        'Away': ['TeamB', 'TeamA', 'TeamB'],
        'Res': [2, 0, 2],  # Home win, Away win, Home win
        'GF': [2, 1, 3],
        'GA': [1, 2, 0]
    })

    result = compute_trailing_features(matches, window=3)

    # First match has no history
    assert pd.isna(result.iloc[0]['Home_Avg_GF'])

    # Subsequent matches should have features
    assert 'Home_Avg_GF' in result.columns
    assert 'Away_Avg_GF' in result.columns


# ==============================================
# Integration Tests
# ==============================================

def test_poisson_workflow():
    """Test complete Poisson workflow."""
    # Calculate features
    features = calculate_poisson_features(
        elo_home=1550, elo_away=1450,
        avg_gf_home=1.5, avg_gf_away=1.0,
        avg_ga_home=0.8, avg_ga_away=1.2
    )

    # Verify probabilities are valid
    assert features['Poisson_Home_Win'] + features['Poisson_Draw'] + features['Poisson_Away_Win'] == pytest.approx(1.0, abs=0.001)

    # Verify xG values
    assert features['xG_home'] > features['xG_away']  # Stronger team

    # Verify expected goals
    assert features['Expected_Home_Goals'] == pytest.approx(features['xG_home'], abs=0.01)


def test_elo_with_poisson():
    """Test Elo and Poisson integration."""
    # Start with equal Elo
    home_elo = 1500
    away_elo = 1500

    # Calculate expected goals for equal teams
    features = calculate_poisson_features(
        elo_home=home_elo, elo_away=away_elo,
        avg_gf_home=1.3, avg_gf_away=1.3,
        avg_ga_home=1.0, avg_ga_away=1.0
    )

    # With equal stats, home should have slight advantage
    assert features['Poisson_Home_Win'] > features['Poisson_Away_Win']
    assert features['xG_home'] > features['xG_away']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
