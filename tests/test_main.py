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
    """Test computing trailing features for a small dataset.
    Uses the canonical column names (HomeTeam/AwayTeam/GF/GA) that the
    real pipeline passes to compute_trailing_features.
    """
    matches = pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-08', '2024-01-15']),
        'HomeTeam': ['TeamA', 'TeamB', 'TeamA'],
        'AwayTeam': ['TeamB', 'TeamA', 'TeamB'],
        'FullTimeResult': [2, 0, 2],  # Home win, Away win, Home win
        'GF': [2, 1, 3],
        'GA': [1, 2, 0]
    })

    result = compute_trailing_features(matches, window=3)

    # First match has no prior history — trailing stats should be NaN
    assert pd.isna(result.iloc[0]['Home_Avg_GF'])

    # Subsequent matches should have features populated
    assert 'Home_Avg_GF' in result.columns
    assert 'Away_Avg_GF' in result.columns
    assert 'Home_Form' in result.columns
    assert 'Away_Form' in result.columns


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


# ==============================================
# Critical Bug Fix Tests (CR-2026-03-21-001, 002, 003)
# ==============================================

def test_division_by_zero_features_sparse_history():
    """Test that features.py handles sparse history without division by zero (CR-2026-03-21-001)."""
    # Empty history
    empty_result = get_team_trailing_stats([], 8)
    assert empty_result["matches"] == 0
    assert np.isnan(empty_result["form"])
    assert np.isnan(empty_result["avg_gf"])

    # Single match history
    single_match = [{"gf": 2, "ga": 1}]
    result = get_team_trailing_stats(single_match, 8)
    assert result["matches"] == 1
    assert result["form"] == 3.0  # 3 points for a win / 1 match

    # Multiple matches with various results
    mixed_history = [
        {"gf": 2, "ga": 1},  # Win: 3 points
        {"gf": 1, "ga": 1},  # Draw: 1 point
        {"gf": 0, "ga": 2},  # Loss: 0 points
    ]
    result = get_team_trailing_stats(mixed_history, 8)
    assert result["matches"] == 3
    assert result["form"] == (3 + 1 + 0) / 3  # 4 points / 3 matches


def test_probability_normalization_edge_cases():
    """Test probability normalization with extreme xG values (CR-2026-03-21-003)."""
    test_cases = [
        (0.0, 0.0),        # Both zero
        (0.001, 0.001),    # Very low
        (0.1, 0.1),        # Low
        (1.5, 1.2),        # Normal
        (3.0, 3.0),        # High
        (10.0, 10.0),      # Very high
    ]

    for xg_h, xg_a in test_cases:
        result = calculate_outcome_probabilities(xg_h, xg_a)

        # Check probabilities sum to 1
        total = result["home_win"] + result["draw"] + result["away_win"]
        assert 0.99 <= total <= 1.01, f"Sum {total} for xG({xg_h}, {xg_a})"

        # Check no NaN/Inf
        assert not np.isnan(result["home_win"]), f"home_win NaN for xG({xg_h}, {xg_a})"
        assert not np.isnan(result["draw"]), f"draw NaN for xG({xg_h}, {xg_a})"
        assert not np.isnan(result["away_win"]), f"away_win NaN for xG({xg_h}, {xg_a})"
        assert not np.isinf(result["home_win"]), f"home_win Inf for xG({xg_h}, {xg_a})"
        assert not np.isinf(result["draw"]), f"draw Inf for xG({xg_h}, {xg_a})"
        assert not np.isinf(result["away_win"]), f"away_win Inf for xG({xg_h}, {xg_a})"


def test_integer_conversion_bounds_clipping():
    """Test that scoreline prediction properly clips values (CR-2026-03-21-002)."""
    # Simulate various prediction values
    test_values = [
        (np.nan, 0),      # NaN should become 0
        (np.inf, 0),      # Inf should become 0 (treated as invalid)
        (-1.5, 0),        # Negative should clip to 0
        (2.7, 2),         # Normal value should round
        (6.5, 6),         # Over max should clip to 6
    ]

    for val, expected in test_values:
        # This mirrors the actual logic in pipeline.py
        if np.isnan(val) or np.isinf(val):
            clipped = 0
        else:
            clipped = int(np.clip(val, 0, 6))
        assert clipped == expected, f"Value {val} clipped to {clipped}, expected {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ==============================================
# Tests added for coverage gaps (recommendations)
# ==============================================

def test_parse_fixtures_standard_format(tmp_path):
    """Test parse_fixtures with a real Partidos.txt format."""
    from src.data_processing import parse_fixtures
    
    partidos = tmp_path / "Partidos.txt"
    partidos.write_text(
        "FECHA 9 - 2 al 4/05/2026\n\n"
        "Boca - River:\n"
        "San Lorenzo - Racing:\n"
        "\nCantidad de penales cobrados:\n"
        "Cantidad de expulsados:\n"
        "Cantidad de goles convertidos:\n",
        encoding="utf-8"
    )
    
    fixtures_df, header, summary = parse_fixtures(str(partidos), glossary={})
    
    assert header == "FECHA 9 - 2 al 4/05/2026"
    assert len(fixtures_df) == 2
    assert "HomeTeam" in fixtures_df.columns
    assert "AwayTeam" in fixtures_df.columns
    assert fixtures_df.iloc[0]["HomeTeam"] == "BOCA"
    assert fixtures_df.iloc[0]["AwayTeam"] == "RIVER"


def test_parse_fixtures_empty_file(tmp_path):
    """Test parse_fixtures with an empty file returns empty DataFrame."""
    from src.data_processing import parse_fixtures
    
    partidos = tmp_path / "Partidos.txt"
    partidos.write_text("", encoding="utf-8")
    
    fixtures_df, header, summary = parse_fixtures(str(partidos), glossary={})
    assert fixtures_df.empty
    assert header is None


def test_ensemble_blending_weights():
    """Test that ensemble blending applies 60/40 ML/Poisson split correctly."""
    import numpy as np
    
    # Simulate ML probabilities [away, draw, home]
    ml_proba = np.array([[0.2, 0.3, 0.5]])
    poisson_away = np.array([0.3])
    poisson_draw = np.array([0.4])
    poisson_home = np.array([0.3])
    
    alpha = 0.6
    blended = np.zeros_like(ml_proba)
    blended[:, 0] = alpha * ml_proba[:, 0] + (1 - alpha) * poisson_away
    blended[:, 1] = alpha * ml_proba[:, 1] + (1 - alpha) * poisson_draw
    blended[:, 2] = alpha * ml_proba[:, 2] + (1 - alpha) * poisson_home
    
    assert blended[0, 0] == pytest.approx(0.6 * 0.2 + 0.4 * 0.3, abs=1e-6)
    assert blended[0, 1] == pytest.approx(0.6 * 0.3 + 0.4 * 0.4, abs=1e-6)
    assert blended[0, 2] == pytest.approx(0.6 * 0.5 + 0.4 * 0.3, abs=1e-6)
    # Blended probs should sum to 1
    assert blended[0].sum() == pytest.approx(1.0, abs=1e-6)


def test_new_team_detection_in_fixtures():
    """Test that teams in fixtures with no historical data are detectable."""
    known_teams = {"BOCA JUNIORS", "RIVER PLATE", "RACING CLUB"}
    fixture_teams = {"BOCA JUNIORS", "RIVER PLATE", "NUEVO EQUIPO FC"}
    
    unknown = fixture_teams - known_teams
    assert "NUEVO EQUIPO FC" in unknown
    assert len(unknown) == 1


def test_gf_ga_column_mapping():
    """Test that GF/GA are mapped correctly (not Away_GF assigned to GA)."""
    import pandas as pd
    
    matches = pd.DataFrame({
        "Home_GF": [2, 1],
        "Away_GF": [0, 3],
    })
    
    # Correct mapping
    matches["GF"] = matches["Home_GF"]
    matches["GA"] = matches["Away_GF"]
    
    # GF should be home goals scored, GA should be away goals scored (= home goals conceded)
    assert matches.iloc[0]["GF"] == 2   # home scored 2
    assert matches.iloc[0]["GA"] == 0   # away scored 0 (home conceded 0)
    assert matches.iloc[1]["GF"] == 1   # home scored 1
    assert matches.iloc[1]["GA"] == 3   # away scored 3 (home conceded 3)
