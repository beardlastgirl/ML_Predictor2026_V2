"""Tests for Phase 1.1 sporting-form variants (EWMA decay, venue splits)."""

import numpy as np
import pandas as pd
import pytest

from src.batched_features import (
    _ewma_stats,
    _venue_stats,
    compute_trailing_features_batched,
)
from src.config import VENUE_SPLIT_MIN_MATCHES

assert VENUE_SPLIT_MIN_MATCHES >= 1  # sanity for the fixtures below


def _history(entries):
    """entries: list of (gf, ga, is_home) in chronological order."""
    return [{"gf": gf, "ga": ga, "is_home": h} for gf, ga, h in entries]


def test_ewma_handcomputed_values():
    history = _history([(2, 0, True), (1, 1, True), (0, 2, False)])
    stats = _ewma_stats(history, window=8, halflife=2)
    decay = 0.5 ** 0.5
    w = np.array([decay**2, decay, 1.0])
    wsum = w.sum()
    pts = np.array([3.0, 1.0, 0.0])
    gf = np.array([2.0, 1.0, 0.0])
    ga = np.array([0.0, 1.0, 2.0])
    assert stats["form"] == pytest.approx((w * pts).sum() / wsum, abs=1e-12)
    assert stats["gf"] == pytest.approx((w * gf).sum() / wsum, abs=1e-12)
    assert stats["ga"] == pytest.approx((w * ga).sum() / wsum, abs=1e-12)


def test_ewma_prefers_recent_over_oldest():
    old_heavy = _history([(5, 0, True)] + [(0, 0, True)] * 4)
    new_heavy = _history([(0, 0, True)] * 4 + [(5, 0, True)])
    assert _ewma_stats(new_heavy, 8, 2)["gf"] > _ewma_stats(old_heavy, 8, 2)["gf"]


def test_ewma_nan_only_when_history_empty():
    stats = _ewma_stats([], window=8, halflife=4)
    assert np.isnan(stats["form"]) and np.isnan(stats["gf"]) and np.isnan(stats["ga"])
    stats = _ewma_stats(_history([(1, 0, True)]), window=8, halflife=4)
    assert stats["form"] == 3.0 and stats["gf"] == 1.0 and stats["ga"] == 0.0


def test_venue_fallback_when_insufficient_venue_history():
    # (VENUE_SPLIT_MIN_MATCHES - 1) home matches + several away matches
    home_entries = [(3, 1, True)] * (VENUE_SPLIT_MIN_MATCHES - 1)
    away_entries = [(0, 2, False)] * 5
    stats = _venue_stats(_history(home_entries + away_entries), window=8, is_home=True)
    overall = _history(home_entries + away_entries)
    gf_all = np.mean([m["gf"] for m in overall])
    assert stats["gf"] == pytest.approx(gf_all, abs=1e-12)  # fell back to overall


def test_venue_split_uses_only_matching_venue():
    home_entries = [(4, 0, True)] * VENUE_SPLIT_MIN_MATCHES
    away_entries = [(0, 3, False)] * 4
    stats = _venue_stats(_history(home_entries + away_entries), window=8, is_home=True)
    assert stats["gf"] == pytest.approx(4.0, abs=1e-12)
    assert stats["ga"] == pytest.approx(0.0, abs=1e-12)
    assert stats["form"] == pytest.approx(3.0, abs=1e-12)


def _matches(rows):
    return pd.DataFrame(rows, columns=["Date", "Time", "Home", "Away", "GF", "GA"])


@pytest.mark.parametrize("variant", [{"type": "ewma", "halflife": 2}, {"type": "venue_split"}])
def test_variant_batch_isolation_same_timestamp(variant):
    """Changing one same-timestamp result must not change a peer's variant features."""
    baseline = _matches([
        ("2026-01-01", "12:00", "A", "Z", 2, 0),
        ("2026-01-02", "18:00", "A", "B", 3, 0),  # changed in second run
        ("2026-01-02", "18:00", "A", "C", 1, 0),  # peer
        ("2026-01-03", "12:00", "A", "D", 1, 0),
    ])
    changed = baseline.copy()
    changed.loc[1, ["GF", "GA"]] = [0, 3]
    first = compute_trailing_features_batched(baseline, window=8, form_variant=variant)
    second = compute_trailing_features_batched(changed, window=8, form_variant=variant)
    variant_cols = [c for c in first.columns if "_EWMA_" in c or "_Venue_" in c]
    assert variant_cols, "variant produced no variant columns"
    peer_first = first[(first.Home == "A") & (first.Away == "C")][variant_cols].iloc[0]
    peer_second = second[(second.Home == "A") & (second.Away == "C")][variant_cols].iloc[0]
    pd.testing.assert_series_equal(peer_first, peer_second, check_names=False)


def test_baseline_columns_unchanged_without_variant():
    df = _matches([
        ("2026-01-01", "12:00", "A", "B", 2, 0),
        ("2026-01-02", "12:00", "A", "C", 1, 1),
    ])
    out = compute_trailing_features_batched(df, window=8)
    assert not any("_EWMA_" in c or "_Venue_" in c for c in out.columns)
    assert {"Home_Avg_GF", "Away_Form", "Home_Matches"}.issubset(out.columns)
