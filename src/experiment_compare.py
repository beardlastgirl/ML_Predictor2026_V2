"""Paired match-level comparison of two experiments on identical OOF rows.

Usage:
    python -m src.experiment_compare BASELINE_NAME VARIANT_NAME

Loads the LATEST record per name from experiments/results.jsonl and its
per-match OOF probability file, then computes per-match log-loss and Brier
deltas (variant - baseline) with a paired bootstrap 95% CI. Decision rule
(predefined): a variant is a credible improvement only if the log-loss CI
lies entirely below 0; entirely above 0 is a degradation; anything crossing
0 is inconclusive -> keep the baseline.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS_LOG = Path("experiments/results.jsonl")
N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 42
EPS = 1e-15  # mirrors sklearn log-loss clipping


def _latest_record(name: str) -> dict:
    records = [
        json.loads(line)
        for line in open(RESULTS_LOG, encoding="utf-8")
        if json.loads(line)["name"] == name
    ]
    if not records:
        raise SystemExit(f"No experiment named '{name}' in {RESULTS_LOG}")
    rec = records[-1]
    if rec["error"]:
        raise SystemExit(f"Latest '{name}' record has an error:\n{rec['error']}")
    return rec


def _per_match(rec: dict) -> pd.DataFrame:
    oof = pd.read_csv(rec["oof_file"])
    p = oof[["p_away", "p_draw", "p_home"]].to_numpy()
    y = oof["y_true"].to_numpy().astype(int)
    p_true = np.clip(p[np.arange(len(oof)), y], EPS, 1.0)
    oof["ll"] = -np.log(p_true)
    oof["brier"] = np.sum((p - np.eye(3)[y]) ** 2, axis=1)
    return oof[["pos", "fold", "y_true", "ll", "brier"]]


def _bootstrap_ci(delta: np.ndarray) -> tuple:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    idx = rng.integers(0, len(delta), size=(N_BOOTSTRAP, len(delta)))
    means = delta[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def compare(baseline_name: str, variant_name: str) -> dict:
    base_rec, var_rec = _latest_record(baseline_name), _latest_record(variant_name)
    base, var = _per_match(base_rec), _per_match(var_rec)
    if len(base) != len(var) or not (base["pos"].to_numpy() == var["pos"].to_numpy()).all():
        raise SystemExit("OOF row sets differ; experiments are not comparable.")
    if not (base["y_true"].to_numpy() == var["y_true"].to_numpy()).all():
        raise SystemExit("OOF label alignment differs; experiments are not comparable.")

    ll_delta = (var["ll"] - base["ll"]).to_numpy()
    br_delta = (var["brier"] - base["brier"]).to_numpy()
    ll_ci = _bootstrap_ci(ll_delta)
    br_ci = _bootstrap_ci(br_delta)

    per_fold = (
        pd.DataFrame({"fold": base["fold"], "ll_delta": ll_delta, "brier_delta": br_delta})
        .groupby("fold")
        .mean()
    )

    result = {
        "baseline": base_rec["experiment_id"],
        "variant": var_rec["experiment_id"],
        "oof_n": int(len(base)),
        "mean_ll_delta": float(ll_delta.mean()),
        "ll_ci95": list(ll_ci),
        "mean_brier_delta": float(br_delta.mean()),
        "brier_ci95": list(br_ci),
        "per_fold_ll_delta": {int(k): float(v) for k, v in per_fold["ll_delta"].items()},
        "baseline_mean_ll": base_rec["aggregate"]["mean_log_loss"],
        "variant_mean_ll": var_rec["aggregate"]["mean_log_loss"],
        "baseline_brier": base_rec["aggregate"]["brier_multiclass"],
        "variant_brier": var_rec["aggregate"]["brier_multiclass"],
        "verdict": (
            "IMPROVEMENT" if ll_ci[1] < 0
            else "DEGRADATION" if ll_ci[0] > 0
            else "INCONCLUSIVE"
        ),
    }
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m src.experiment_compare BASELINE_NAME VARIANT_NAME")
        return 1
    r = compare(sys.argv[1], sys.argv[2])
    print(f"Baseline: {r['baseline']} (mean ll {r['baseline_mean_ll']:.4f}, brier {r['baseline_brier']:.4f})")
    print(f"Variant:  {r['variant']} (mean ll {r['variant_mean_ll']:.4f}, brier {r['variant_brier']:.4f})")
    print(f"OOF rows: {r['oof_n']}")
    print(f"LL delta:    {r['mean_ll_delta']:+.5f}  95% CI [{r['ll_ci95'][0]:+.5f}, {r['ll_ci95'][1]:+.5f}]")
    print(f"Brier delta: {r['mean_brier_delta']:+.5f}  95% CI [{r['brier_ci95'][0]:+.5f}, {r['brier_ci95'][1]:+.5f}]")
    print("Per-fold LL delta: " + ", ".join(f"f{k}={v:+.5f}" for k, v in r["per_fold_ll_delta"].items()))
    print(f"VERDICT: {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
