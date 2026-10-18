"""Tests for Phase 1.1 sporting-form variants (EWMA decay, venue splits)."""

import numpy as np
import pandas as pd
import pytest

from src.batched_features import (
    _ewma_stats,
    _multi_window_stats,
    _venue_stats,
    compute_trailing_features_batched,
)
from src.config import ROLLING_WINDOW_CANDIDATES, VENUE_SPLIT_MIN_MATCHES

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


@pytest.mark.parametrize("variant", [
    {"type": "ewma", "halflife": 2},
    {"type": "venue_split"},
    {"type": "multi_window", "windows": list(ROLLING_WINDOW_CANDIDATES)},
])
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
    variant_cols = [c for c in first.columns if "_EWMA_" in c or "_Venue_" in c or "_Roll" in c]
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
    assert not any("_EWMA_" in c or "_Venue_" in c or "_Roll" in c for c in out.columns)
    assert {"Home_Avg_GF", "Away_Form", "Home_Matches"}.issubset(out.columns)


# --- Phase 1.2: multi-window rolling PPG / GD variant ------------------------


def test_multi_window_hand_computed_values():
    # 12 chronological results; expectations derived independently below.
    results = [(3, 0), (0, 3), (1, 1), (2, 2), (1, 0),
               (2, 0), (2, 0), (1, 1), (0, 1), (3, 1),
               (2, 1), (0, 0)]
    history = _history([(gf, ga, True) for gf, ga in results])
    stats = _multi_window_stats(history, [5, 10])
    last5 = results[-5:]
    pts5 = sum(3.0 if g > a else 1.0 if g == a else 0.0 for g, a in last5)
    gd5 = sum(g - a for g, a in last5) / 5.0
    last10 = results[-10:]
    pts10 = sum(3.0 if g > a else 1.0 if g == a else 0.0 for g, a in last10)
    gd10 = sum(g - a for g, a in last10) / 10.0
    assert stats["form@5"] == pytest.approx(pts5 / 5.0, abs=1e-12)
    assert stats["gd@5"] == pytest.approx(gd5, abs=1e-12)
    assert stats["form@10"] == pytest.approx(pts10 / 10.0, abs=1e-12)
    assert stats["gd@10"] == pytest.approx(gd10, abs=1e-12)


def test_multi_window_truncates_to_available_matches():
    # Fewer prior matches than the window: uses all of them (k < window).
    history = _history([(2, 0, True), (1, 1, False)])
    stats = _multi_window_stats(history, [5])
    assert stats["form@5"] == pytest.approx((3.0 + 1.0) / 2, abs=1e-12)
    assert stats["gd@5"] == pytest.approx((2 - 0 + 1 - 1) / 2, abs=1e-12)


def test_multi_window_nan_only_when_history_empty():
    stats = _multi_window_stats([], [5, 10])
    assert np.isnan(stats["form@5"]) and np.isnan(stats["gd@5"])
    assert np.isnan(stats["form@10"]) and np.isnan(stats["gd@10"])
    stats = _multi_window_stats(_history([(1, 0, True)]), [5, 10])
    assert stats["form@5"] == 3.0 and stats["gd@5"] == 1.0
    assert stats["form@10"] == 3.0 and stats["gd@10"] == 1.0


def test_multi_window_ignores_matches_older_than_window():
    # Perturbing a match inside the last 10 but outside the last 5 must
    # change Roll10 and leave Roll5 unchanged (hard-window semantics on the
    # batched path, not just the helper).
    variant = {"type": "multi_window", "windows": [5, 10]}
    rows_a = [
        (f"2026-01-{d:02d}", "12:00", "A", f"T{d}", 4, 4) for d in range(1, 12)
    ] + [("2026-02-01", "12:00", "A", "B", 1, 0)]
    rows_b = [list(r) for r in rows_a]
    rows_b[1][4], rows_b[1][5] = 9, 0  # 2026-01-02: inside last-10, outside last-5
    out_a = compute_trailing_features_batched(_matches(rows_a), window=8, form_variant=variant)
    out_b = compute_trailing_features_batched(_matches(rows_b), window=8, form_variant=variant)
    tgt_a = out_a[(out_a.Home == "A") & (out_a.Away == "B")].iloc[0]
    tgt_b = out_b[(out_b.Home == "A") & (out_b.Away == "B")].iloc[0]
    # Roll5 spans positions 7..11 (all draws): perturbation invisible.
    assert tgt_a["Home_Roll5_Form"] == pytest.approx(1.0, abs=1e-12)
    assert tgt_a["Home_Roll5_GD"] == pytest.approx(0.0, abs=1e-12)
    assert tgt_b["Home_Roll5_Form"] == pytest.approx(1.0, abs=1e-12)
    assert tgt_b["Home_Roll5_GD"] == pytest.approx(0.0, abs=1e-12)
    # Roll10 spans positions 2..11: one win (3 pts) + nine draws (9 pts).
    assert tgt_a["Home_Roll10_Form"] == pytest.approx(1.0, abs=1e-12)
    assert tgt_a["Home_Roll10_GD"] == pytest.approx(0.0, abs=1e-12)
    assert tgt_b["Home_Roll10_Form"] == pytest.approx((3.0 + 9 * 1.0) / 10, abs=1e-12)
    assert tgt_b["Home_Roll10_GD"] == pytest.approx(9 / 10, abs=1e-12)


def test_multi_window_no_future_leakage_across_timestamps():
    # Changing a LATER match's result must not change an EARLIER match's
    # rolling features (temporal leakage check on the batched path).
    rows = [
        ("2026-01-01", "12:00", "A", "B", 2, 0),
        ("2026-01-02", "12:00", "A", "C", 1, 1),
        ("2026-01-03", "12:00", "A", "D", 0, 2),
    ]
    variant = {"type": "multi_window", "windows": list(ROLLING_WINDOW_CANDIDATES)}
    out_a = compute_trailing_features_batched(_matches(rows), window=8, form_variant=variant)
    rows_changed = [list(r) for r in rows]
    rows_changed[2][4], rows_changed[2][5] = 5, 0
    out_b = compute_trailing_features_batched(_matches(rows_changed), window=8, form_variant=variant)
    roll_cols = [c for c in out_a.columns if "_Roll" in c]
    for i in (0, 1):  # row 1 has non-NaN rolling features from one prior match
        pd.testing.assert_series_equal(
            out_a.iloc[i][roll_cols], out_b.iloc[i][roll_cols], check_names=False
        )
