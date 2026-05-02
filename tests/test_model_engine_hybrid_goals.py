"""
Tests for _calculate_hybrid_goals in src/model_engine.py.

Scoreline logic uses floor(xG) as the base (Poisson mode), not round().
This avoids collapsing Liga Profesional xG values (0.8-1.6) all to 1.

floor(1.2) = 1, floor(0.8) = 0, floor(1.8) = 1, floor(0.6) = 0
"""
import pytest
from src.model_engine import _calculate_hybrid_goals


def test_pure_poisson_floor():
    """floor(xG) is used as base, not round()."""
    # floor(1.2)=1, floor(0.8)=0; ml_pred=2 home win, p_h=0.4 >= 0.35
    # home win: m_h=1 > m_a=0 already, p_h < 0.50 so no bump
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, 0.4, 0.3, 0.3
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_h > actual_a  # home win predicted and enforced
    assert actual_h == 1
    assert actual_a == 0


def test_poisson_floor_away_higher():
    """floor(0.6)=0, floor(1.8)=1; away win predicted."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.6, 1.8, 0, 0.1, 0.2, 0.7
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_a > actual_h  # away win enforced
    assert actual_a == 2  # p_a=0.7 >= 0.50 → bump m_a += 1 → 1+1=2


def test_high_confidence_home_win():
    """p_h=0.7 >= 0.50 triggers bump: m_h = floor(1.2)+1 = 2."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, 0.7, 0.2, 0.1
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_h == 2
    assert actual_a == 0


def test_high_confidence_away_win():
    """p_a=0.7 >= 0.50 triggers bump: m_a = floor(1.2)+1 = 2."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.8, 1.2, 0, 0.1, 0.2, 0.7
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_a == 2
    assert actual_h == 0


def test_high_confidence_draw():
    """Draw: m_h = m_a = max(floor(1.2), floor(1.8)) = max(1,1) = 1."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 1.8, 1, 0.2, 0.6, 0.2
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_h == actual_a  # draw
    assert actual_h == 1


def test_low_confidence_no_adjustment():
    """max_prob=0.34 < 0.35 threshold → no ML adjustment, pure floor(xG)."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, 0.34, 0.33, 0.33
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    # floor(1.2)=1, floor(0.8)=0, no adjustment
    assert actual_h == 1
    assert actual_a == 0


def test_max_goals_cap():
    """Goals capped at MAX_PREDICTED_GOALS=6."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 7.0, 7.0, 1, 0.5, 0.3, 0.2
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_h == 6
    assert actual_a == 6


def test_zero_goals():
    """Negative xG produces zero goals."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = -0.5, -0.5, 1, 0.3, 0.4, 0.3
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    assert actual_h == 0
    assert actual_a == 0


def test_fractional_floor():
    """floor(0.5)=0, floor(1.5)=1 — floor differs from round for .5 values."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 0.5, 1.5, 1, 0.33, 0.34, 0.33
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    # max_prob=0.34 < 0.35 → no adjustment; floor(0.5)=0, floor(1.5)=1
    assert actual_h == 0
    assert actual_a == 1


def test_threshold_boundary():
    """max_prob exactly at 0.35 triggers adjustment."""
    exp_h, exp_a, ml_pred, p_h, p_d, p_a = 1.2, 0.8, 2, 0.35, 0.35, 0.30
    actual_h, actual_a = _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a)
    # max_prob=0.35 >= 0.35, ml_pred=2, p_h=0.35 >= p_d and p_a
    # m_h=1 > m_a=0 already, p_h < 0.50 so no bump
    assert actual_h >= actual_a
