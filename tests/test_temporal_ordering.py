"""Production-path regression tests for atomic historical feature batches."""

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from src.config import BASE_ELO
from src.pipeline import build_features


TEMPORAL_FEATURES = [
    "Home_Elo", "Away_Elo", "Home_Avg_GF", "Away_Avg_GF",
    "Home_Avg_GA", "Away_Avg_GA", "Home_Form", "Away_Form",
    "xG_home", "xG_away", "Poisson_Home_Win", "Poisson_Draw",
    "Poisson_Away_Win", "Elo_Diff", "Attack_Balance", "Def_Balance",
    "Form_Balance",
]


def _matches(rows):
    """Small, fully valid input for the real build_features path."""
    frame = pd.DataFrame(rows, columns=["Match_ID", "Date", "Time", "Home", "Away", "HG", "AG", "Res"])
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["B365CH"] = 2.0
    frame["B365CD"] = 3.0
    frame["B365CA"] = 4.0
    return frame


def _by_id(frame):
    return frame.set_index("Match_ID").sort_index()


def _assert_same_features(left, right, match_ids):
    assert_frame_equal(
        _by_id(left).loc[match_ids, TEMPORAL_FEATURES],
        _by_id(right).loc[match_ids, TEMPORAL_FEATURES],
        check_dtype=False,
    )


def _sequential_home_elos(frame):
    """The pre-fix sequential behavior, retained only to prove test sensitivity."""
    from src.stats_engine import update_elo

    ratings, output = {}, {}
    for _, row in frame.sort_values(["Date", "Time"], kind="stable").iterrows():
        home, away = row.Home, row.Away
        home_elo, away_elo = ratings.get(home, BASE_ELO), ratings.get(away, BASE_ELO)
        output[row.Match_ID] = (home_elo, away_elo)
        ratings[home], ratings[away] = update_elo(home_elo, away_elo, row.Res)
    return output


def test_unsorted_input_is_sorted_before_production_features():
    source = _matches([
        ("late", "2026-01-03", "14:00", "A", "B", 2, 0, 2),
        ("early", "2026-01-03", "10:00", "A", "C", 1, 0, 2),
        ("next", "2026-01-04", "10:00", "A", "D", 0, 1, 0),
    ])
    actual, _ = build_features(source)
    assert actual["Match_ID"].tolist() == ["early", "late", "next"]
    assert _by_id(actual).loc["early", "Home_Elo"] == BASE_ELO
    assert _by_id(actual).loc["late", "Home_Elo"] > BASE_ELO


def test_same_timestamp_result_change_cannot_change_peer_features():
    baseline = _matches([
        ("history", "2026-01-01", "12:00", "A", "Z", 2, 0, 2),
        ("changed", "2026-01-02", "18:00", "A", "B", 3, 0, 2),
        ("peer", "2026-01-02", "18:00", "A", "C", 1, 0, 2),
        ("later", "2026-01-03", "12:00", "A", "D", 1, 0, 2),
    ])
    changed = baseline.copy()
    changed.loc[changed.Match_ID == "changed", ["HG", "AG", "Res"]] = [0, 3, 0]
    first, _ = build_features(baseline)
    second, _ = build_features(changed)
    _assert_same_features(first, second, ["peer"])


def test_shared_team_collision_uses_one_pre_batch_snapshot():
    source = _matches([
        ("history", "2026-01-01", "12:00", "A", "Z", 2, 0, 2),
        ("one", "2026-01-02", "18:00", "A", "B", 3, 0, 2),
        ("two", "2026-01-02", "18:00", "A", "C", 0, 1, 0),
    ])
    actual, _ = build_features(source)
    indexed = _by_id(actual)
    assert indexed.loc["one", "Home_Elo"] == indexed.loc["two", "Home_Elo"]
    assert indexed.loc["one", "Home_Avg_GF"] == indexed.loc["two", "Home_Avg_GF"]
    assert indexed.loc["one", "xG_home"] == indexed.loc["two", "xG_home"]


def test_completed_batch_updates_the_next_batch():
    source = _matches([
        ("first", "2026-01-01", "12:00", "A", "B", 2, 0, 2),
        ("second", "2026-01-02", "12:00", "A", "C", 1, 0, 2),
    ])
    actual, _ = build_features(source)
    indexed = _by_id(actual)
    assert indexed.loc["second", "Home_Elo"] > BASE_ELO
    assert indexed.loc["second", "Home_Avg_GF"] == 2.0
    assert indexed.loc["second", "Home_Form"] == 3.0


def test_regression_fixture_fails_under_old_sequential_semantics():
    source = _matches([
        ("history", "2026-01-01", "12:00", "A", "Z", 2, 0, 2),
        ("one", "2026-01-02", "18:00", "A", "B", 3, 0, 2),
        ("two", "2026-01-02", "18:00", "A", "C", 0, 1, 0),
    ])
    actual, _ = build_features(source)
    sequential = _sequential_home_elos(source)
    atomic = _by_id(actual)
    assert sequential["two"][0] != atomic.loc["two", "Home_Elo"]
    assert sequential["two"][0] != atomic.loc["one", "Home_Elo"]


def test_row_order_inside_timestamp_batch_is_invariant_by_match_identity():
    source = _matches([
        ("history", "2026-01-01", "12:00", "A", "Z", 2, 0, 2),
        ("a", "2026-01-02", "18:00", "A", "B", 3, 0, 2),
        ("b", "2026-01-02", "18:00", "C", "D", 0, 1, 0),
        ("c", "2026-01-02", "18:00", "E", "F", 1, 1, 1),
    ])
    shuffled = pd.concat([source.iloc[:1], source.iloc[[3, 1, 2]]], ignore_index=True)
    first, _ = build_features(source)
    second, _ = build_features(shuffled)
    _assert_same_features(first, second, ["a", "b", "c"])


def test_future_result_cannot_change_earlier_timestamp_features():
    baseline = _matches([
        ("first", "2026-01-01", "12:00", "A", "B", 1, 0, 2),
        ("middle", "2026-01-02", "12:00", "A", "C", 1, 0, 2),
        ("future", "2026-01-03", "12:00", "A", "D", 1, 0, 2),
    ])
    changed = baseline.copy()
    changed.loc[changed.Match_ID == "future", ["HG", "AG", "Res"]] = [0, 4, 0]
    first, _ = build_features(baseline)
    second, _ = build_features(changed)
    _assert_same_features(first, second, ["first", "middle"])


def test_missing_or_midnight_time_batches_the_entire_uncertain_day():
    source = _matches([
        ("midnight", "2026-01-01", "00:30", "A", "B", 2, 0, 2),
        ("known", "2026-01-01", "14:00", "A", "C", 1, 0, 2),
        ("next", "2026-01-02", "12:00", "A", "D", 1, 0, 2),
    ])
    actual, _ = build_features(source)
    indexed = _by_id(actual)
    assert indexed.loc["midnight", "Home_Elo"] == BASE_ELO
    assert indexed.loc["known", "Home_Elo"] == BASE_ELO
    assert indexed.loc["next", "Home_Elo"] > BASE_ELO
