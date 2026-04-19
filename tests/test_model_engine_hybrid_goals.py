import pytest
from src.model_engine import _calculate_hybrid_goals

# Define constants directly in test or mock src.config for isolation
# These values mimic those from src/config.py for testing purposes
TEST_WIN_PROBABILITY_THRESHOLD = 0.45
TEST_DRAW_PROBABILITY_THRESHOLD = 0.38
TEST_MAX_PREDICTED_GOALS = 6

# Mocking the config module if necessary, though direct definition is simpler for these few constants
# from unittest.mock import patch
# @patch('src.model_engine.WIN_PROBABILITY_THRESHOLD', TEST_WIN_PROBABILITY_THRESHOLD)
# @patch('src.model_engine.DRAW_PROBABILITY_THRESHOLD', TEST_DRAW_PROBABILITY_THRESHOLD)
# @patch('src.model_engine.MAX_PREDICTED_GOALS', TEST_MAX_PREDICTED_GOALS)


def test_no_heuristic_adjustment():
    """Test case where no specific heuristic should trigger, just rounded xG."""
    # exp_h, exp_a, ml_pred, p_h, p_d, p_a
    # No xG_diff heuristic, no strong ML prediction, no draw strong prediction
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, 0.4, 0.3, 0.3
    expected_h, expected_a = 1, 1 # Rounded from 1.2, 0.8

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_strong_away_win_xg_diff():
    """Test case for xG_diff > 0.20 (strong away win signal)."""
    # ml_pred should be forced to 0 (Away Win)
    # m_a should be at least m_h + 1
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.5, 1.8, 2, 0.3, 0.3, 0.4 # Original ml_pred is Home Win
    # xG_diff = 1.8 - 0.5 = 1.3 > 0.20
    # Initial rounded: m_h=1, m_a=2 (as m_a <= m_h is false here)
    # The condition `if m_a <= m_h: m_a = m_h + 1` is not met here, as m_a (2) is already > m_h (1)
    # But if m_a was 1 and m_h was 1, m_a would become 2
    # Let's adjust expected for the original logic where ml_pred is forced to 0
    # The ml_pred is effectively ignored here, only the goals are adjusted.
    # Initial rounded goals: m_h = 1, m_a = 2. Since m_a > m_h, no further adjustment to m_a.
    expected_h, expected_a = 1, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_medium_away_win_xg_diff_and_proba():
    """Test case for xG_diff > 0.10 and p_a > p_d (medium away win signal)."""
    # ml_pred should be forced to 0 (Away Win)
    # m_a should be at least m_h + 1
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.8, 1.3, 2, 0.3, 0.3, 0.4 # xG_diff = 0.5, p_a > p_d, original ml_pred Home Win
    # Initial rounded: m_h=1, m_a=1
    # Condition `if m_a <= m_h` will be true, m_a becomes m_h + 1 = 2
    expected_h, expected_a = 1, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_home_win_ml_pred_and_proba():
    """Test case for ml_pred == 2 (Home Win) and p_h >= WIN_PROBABILITY_THRESHOLD."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, TEST_WIN_PROBABILITY_THRESHOLD + 0.01, 0.2, 0.1
    # Initial rounded: m_h=1, m_a=1
    # Condition `if m_h <= m_a` will be true, m_h becomes m_a + 1 = 2
    expected_h, expected_a = 2, 1

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_away_win_ml_pred_and_proba():
    """Test case for ml_pred == 0 (Away Win) and p_a >= WIN_PROBABILITY_THRESHOLD."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.8, 1.2, 0, 0.1, 0.2, TEST_WIN_PROBABILITY_THRESHOLD + 0.01
    # Initial rounded: m_h=1, m_a=1
    # Condition `if m_a <= m_h` will be true, m_a becomes m_h + 1 = 2
    expected_h, expected_a = 1, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_ml_pred_and_proba_low_total_xg():
    """Test case for ml_pred == 1 (Draw) and p_d >= DRAW_PROBABILITY_THRESHOLD, low total_xg."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.3, 0.2, 1, TEST_WIN_PROBABILITY_THRESHOLD - 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1
    # total_xg = 0.5. Since total_xg < 0.6, m_h = m_a = 0
    expected_h, expected_a = 0, 0

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_ml_pred_and_proba_medium_low_total_xg():
    """Test case for ml_pred == 1 (Draw) and p_d >= DRAW_PROBABILITY_THRESHOLD, medium low total_xg."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.8, 0.9, 1, TEST_WIN_PROBABILITY_THRESHOLD - 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1
    # total_xg = 1.7. Since 1.0 <= total_xg < 2.5, m_h = m_a = 1
    expected_h, expected_a = 1, 1

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_ml_pred_and_proba_medium_high_total_xg():
    """Test case for ml_pred == 1 (Draw) and p_d >= DRAW_PROBABILITY_THRESHOLD, medium high total_xg."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.6, 1.8, 1, TEST_WIN_PROBABILITY_THRESHOLD - 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1
    # total_xg = 3.4. Since 2.5 <= total_xg < 3.5, m_h = m_a = 2
    expected_h, expected_a = 2, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_ml_pred_and_proba_high_total_xg():
    """Test case for ml_pred == 1 (Draw) and p_d >= DRAW_PROBABILITY_THRESHOLD, high total_xg."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 2.0, 2.5, 1, TEST_WIN_PROBABILITY_THRESHOLD - 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1
    # total_xg = 4.5. Else case: m_h = m_a = min(3, max(2, round(4.5 / 2))) = min(3, max(2, 2)) = 2
    expected_h, expected_a = 2, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_ml_pred_and_proba_high_total_xg_another_case():
    """Test case for ml_pred == 1 (Draw) and p_d >= DRAW_PROBABILITY_THRESHOLD, very high total_xg."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 3.0, 3.5, 1, TEST_WIN_PROBABILITY_THRESHOLD - 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1
    # total_xg = 6.5. Else case: m_h = m_a = min(3, max(2, round(6.5 / 2))) = min(3, max(2, 3)) = 3
    expected_h, expected_a = 3, 3

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_xg_diff_internal_nudge_home():
    """Test draw with significant positive xG_diff_internal, nudging home goals."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.8, 1.2, 1, 0.3, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.1 # total_xg = 3.0, m_h = m_a = 2
    # xG_diff_internal = 0.6 > 0.4. m_h should become min(2+1, 6) = 3. m_a = max(1, 2) = 2
    expected_h, expected_a = 3, 2

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_draw_xg_diff_internal_nudge_away():
    """Test draw with significant negative xG_diff_internal, nudging away goals."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 1.8, 1, 0.1, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.3 # total_xg = 3.0, m_h = m_a = 2
    # xG_diff_internal = -0.6 < -0.4. m_a should become min(2+1, 6) = 3. m_h = max(1, 2) = 2
    expected_h, expected_a = 2, 3

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_max_predicted_goals_limit():
    """Test that goals do not exceed MAX_PREDICTED_GOALS."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 7.0, 7.0, 1, 0.3, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.3
    # Initial rounded: m_h=7, m_a=7. Should be capped at TEST_MAX_PREDICTED_GOALS (6)
    expected_h, expected_a = TEST_MAX_PREDICTED_GOALS, TEST_MAX_PREDICTED_GOALS

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"

def test_min_predicted_goals_limit():
    """Test that goals do not go below 0 (though unlikely with round(exp_x))."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = -0.5, -0.5, 1, 0.3, TEST_DRAW_PROBABILITY_THRESHOLD + 0.01, 0.3
    # Initial rounded: m_h=0, m_a=0. Already >= 0, but final max(0, ..) ensures it.
    expected_h, expected_a = 0, 0

    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert (actual_h, actual_a) == (expected_h, expected_a), 
        f"Expected ({expected_h}, {expected_a}), got ({actual_h}, {actual_a})"
