"""Deliverable 1: overlap audit for proposed rolling-form window variants.

Proposed candidates (hard windows 5 and 10):
  PPG@5, PPG@10  (points-per-game == existing `form` statistic)
  GD@5,  GD@10   (goal difference per match == existing `avg_gd` statistic)

Existing signals covering the same information:
  Home/Away_Form, Home/Away_Avg_GF/GA (hard window TRAILING_WINDOW=8)
  Home/Away_EWMA_Form/GF/GA (halflife 2/4/8, already evaluated D1)
  Home/Away_Avg_GD (computed in pipeline; not in FEATURE_COLUMNS)

Method: compute candidates with the SAME batched timestamp machinery
(window=5, window=10) on a scratch copy, align by _temporal_row_id,
then measure Pearson |r| against the existing counterparts on the
eligible (non-NaN baseline) rows only. No pipeline files are modified.
"""

import numpy as np
import pandas as pd

from src.pipeline import load_data
from src.batched_features import compute_trailing_features_batched
from src.config import TRAILING_WINDOW


def main():
    _, _, matches, _ = load_data()
    matches = matches.copy()
    matches["GF"] = matches["HG"] if "HG" in matches.columns else 0
    matches["GA"] = matches["AG"] if "AG" in matches.columns else 0

    base = compute_trailing_features_batched(matches, window=TRAILING_WINDOW)
    w5 = compute_trailing_features_batched(matches, window=5).add_suffix("_w5")
    w10 = compute_trailing_features_batched(matches, window=10).add_suffix("_w10")
    ewma2 = compute_trailing_features_batched(matches, window=TRAILING_WINDOW,
                                              form_variant={"type": "ewma", "halflife": 2})
    ewma4 = compute_trailing_features_batched(matches, window=TRAILING_WINDOW,
                                              form_variant={"type": "ewma", "halflife": 4})

    n = len(base)
    assert len(w5) == len(w10) == len(ewma2) == len(ewma4) == n

    df = pd.DataFrame({
        "Home_Form8": base["Home_Form"],
        "Home_GD8": base["Home_Avg_GD"],
        "Home_PPG5": w5["Home_Form_w5"],
        "Home_GD5": w5["Home_Avg_GD_w5"],
        "Home_PPG10": w10["Home_Form_w10"],
        "Home_GD10": w10["Home_Avg_GD_w10"],
        "Home_EWMA_F_hl2": ewma2["Home_EWMA_Form"],
        "Home_EWMA_F_hl4": ewma4["Home_EWMA_Form"],
        "Home_EWMA_GD_hl2": ewma2["Home_EWMA_GF"] - ewma2["Home_EWMA_GA"],
        "Home_EWMA_GD_hl4": ewma4["Home_EWMA_GF"] - ewma4["Home_EWMA_GA"],
    })

    # Eligible rows only (baseline NaN pattern): form is NaN iff no history.
    elig = df.dropna(subset=["Home_Form8"]).copy()
    print(f"rows total={n}, eligible={len(elig)}")

    candidates = ["Home_PPG5", "Home_PPG10", "Home_GD5", "Home_GD10"]
    existing = ["Home_Form8", "Home_GD8",
                "Home_EWMA_F_hl2", "Home_EWMA_F_hl4",
                "Home_EWMA_GD_hl2", "Home_EWMA_GD_hl4"]

    corr = elig[candidates + existing].corr()
    print("\n|r| of each candidate vs existing signals (Home side):")
    for c in candidates:
        row = corr.loc[c, existing].abs().sort_values(ascending=False)
        top = ", ".join(f"{k}={v:.3f}" for k, v in row.items())
        print(f"  {c:12s} max|r|={row.iloc[0]:.3f}  [{top}]")

    print("\nInter-candidate correlations (redundancy inside the candidate set):")
    inner = elig[candidates].corr()
    for c in candidates:
        others = {k: v for k, v in inner.loc[c].items() if k != c}
        top = max(others.items(), key=lambda kv: abs(kv[1]))
        print(f"  {c:12s} vs {top[0]:12s} r={top[1]:.3f}")

    # Same check for the Away side (symmetric expectation; verify, don't assume)
    away = pd.DataFrame({
        "Away_Form8": base["Away_Form"],
        "Away_PPG5": w5["Away_Form_w5"],
        "Away_PPG10": w10["Away_Form_w10"],
        "Away_EWMA_F_hl4": ewma4["Away_EWMA_Form"],
    }).dropna(subset=["Away_Form8"])
    ac = away.corr()
    print("\nAway-side spot check |r|:")
    print(f"  PPG5  vs Form8={abs(ac.loc['Away_PPG5','Away_Form8']):.3f} "
          f"vs EWMA_hl4={abs(ac.loc['Away_PPG5','Away_EWMA_F_hl4']):.3f}")
    print(f"  PPG10 vs Form8={abs(ac.loc['Away_PPG10','Away_Form8']):.3f} "
          f"vs EWMA_hl4={abs(ac.loc['Away_PPG10','Away_EWMA_F_hl4']):.3f}")

    # Verdict helper
    print("\nVerdict rules: max|r| >= 0.95 => redundant; 0.85-0.95 => marginal; "
          "< 0.85 vs all => potentially incremental.")


if __name__ == "__main__":
    main()
