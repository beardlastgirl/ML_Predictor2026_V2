"""
Golden regression tests: freeze exact outputs of the mathematical core so
refactors (pipeline splits, feature refactors) cannot silently change
calibrated behavior.

Snapshots captured 2026-09-18 from the verified current implementation.
"""
import numpy as np
import pytest

from src.stats_engine import (
    expected_result, update_elo, calculate_expected_goals,
    calculate_outcome_probabilities, poisson_probability, shin_method,
    calculate_poisson_features,
)
from src.model_engine import _calculate_hybrid_goals
from src.cold_start import calculate_bayesian_shrunk_xg


@pytest.mark.parametrize(
    "elo_team,elo_opp,expected",
    [
        (1500, 1500, 0.5),
        (1565, 1500, 0.5924662305843318),
        (1400, 1500, 0.35993500019711494),
    ],
)
def test_golden_expected_result(elo_team, elo_opp, expected):
    assert expected_result(elo_team, elo_opp) == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize(
    "result,expected_home,expected_away",
    [
        (2, 1508.3676527040732, 1391.6323472959268),  # home win
        (1, 1493.3676527040732, 1406.6323472959268),  # draw
        (0, 1478.3676527040732, 1421.6323472959268),  # away win
    ],
)
def test_golden_update_elo(result, expected_home, expected_away):
    home, away = update_elo(1500.0, 1400.0, result)
    assert home == pytest.approx(expected_home, rel=1e-9)
    assert away == pytest.approx(expected_away, rel=1e-9)


def test_golden_update_elo_clipping():
    home, away = update_elo(2790.0, 2790.0, 2)
    assert home == pytest.approx(2800.0, abs=1e-9)
    assert away == pytest.approx(2777.77398691753, rel=1e-9)


@pytest.mark.parametrize(
    "xG_h,xG_a,exp",
    [
        (1.2, 1.1, (0.38259228716272853, 0.31128143617405146, 0.3061262766632201,
                    1.1999614557656777, 1.099980533370333)),
        (0.5, 0.5, (0.2589142732766382, 0.5118744237437535, 0.22921130297960834,
                    0.49999997061929075, 0.49999997061929075)),
        (2.1, 0.8, (0.6696725541855469, 0.2136629206495828, 0.11666452516487028,
                    2.0975868671488636, 0.7999985042677685)),
    ],
)
def test_golden_outcome_probabilities(xG_h, xG_a, exp):
    o = calculate_outcome_probabilities(xG_h, xG_a)
    exp_hw, exp_d, exp_aw, exp_h, exp_a = exp
    assert o["home_win"] == pytest.approx(exp_hw, rel=1e-9)
    assert o["draw"] == pytest.approx(exp_d, rel=1e-9)
    assert o["away_win"] == pytest.approx(exp_aw, rel=1e-9)
    assert o["expected_home_goals"] == pytest.approx(exp_h, rel=1e-9)
    assert o["expected_away_goals"] == pytest.approx(exp_a, rel=1e-9)


@pytest.mark.parametrize(
    "goals,expected,expected_pmf",
    [
        (0, 1.2, 0.30119421191220214),
        (2, 1.2, 0.2168598325767855),
    ],
)
def test_golden_poisson_pmf(goals, expected, expected_pmf):
    assert poisson_probability(goals, expected) == pytest.approx(expected_pmf, rel=1e-9)


def test_golden_shin_method():
    probs, z = shin_method([2.10, 3.30, 3.60])
    assert probs[0] == pytest.approx(0.4588280880655551, rel=1e-9)
    assert probs[1] == pytest.approx(0.28325098595269127, rel=1e-9)
    assert probs[2] == pytest.approx(0.25792092598175165, rel=1e-9)
    assert z == pytest.approx(0.07944703581033731, rel=1e-6)


def test_golden_shin_method_nan_fallback():
    probs, z = shin_method([np.nan, 2.0, 3.0])
    assert probs.tolist() == pytest.approx([0.333, 0.333, 0.334], abs=1e-12)
    assert z == 0.0


@pytest.mark.parametrize(
    "exp_h,exp_a,ml_pred,p_h,p_d,p_a,expected",
    [
        (1.8, 0.9, 2, 0.5, 0.3, 0.2, (2, 0)),
        (1.8, 0.9, 2, 0.62, 0.2, 0.18, (2, 0)),
        (0.9, 1.8, 0, 0.2, 0.3, 0.5, (0, 2)),
        (0.9, 1.8, 0, 0.15, 0.25, 0.6, (0, 2)),
        (1.2, 1.1, 1, 0.3, 0.4, 0.3, (1, 1)),
        (3.5, 3.6, 1, 0.25, 0.5, 0.25, (3, 3)),
        (0.4, 0.3, 2, 0.55, 0.3, 0.15, (1, 0)),
        (5.2, 1.4, 2, 0.7, 0.2, 0.1, (6, 1)),
        (1.2, 1.2, 2, 0.34, 0.33, 0.33, (1, 1)),
    ],
)
def test_golden_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a, expected):
    assert _calculate_hybrid_goals(exp_h, exp_a, ml_pred, p_h, p_d, p_a) == expected


def test_golden_bayesian_shrink():
    assert calculate_bayesian_shrunk_xg(2.5, 3) == pytest.approx(1.65625, rel=1e-9)


def test_golden_poisson_features():
    pf = calculate_poisson_features(1500, 1400, 1.5, 1.2, 1.1, 1.3)
    assert pf["xG_home"] == pytest.approx(1.65393, rel=1e-9)
    assert pf["xG_away"] == pytest.approx(1.1323529411764706, rel=1e-9)
    assert pf["xG_diff"] == pytest.approx(0.5215770588235293, rel=1e-9)
    assert pf["Poisson_Home_Win"] == pytest.approx(0.49278360889101525, rel=1e-9)
    assert pf["Poisson_Draw"] == pytest.approx(0.26799831410956637, rel=1e-9)
    assert pf["Poisson_Away_Win"] == pytest.approx(0.2392180769994183, rel=1e-9)
    assert pf["Expected_Home_Goals"] == pytest.approx(1.653490593732532, rel=1e-9)
    assert pf["Expected_Away_Goals"] == pytest.approx(1.132328476330588, rel=1e-9)
    assert pf["Expected_Total_Goals"] == pytest.approx(2.78581907006312, rel=1e-9)