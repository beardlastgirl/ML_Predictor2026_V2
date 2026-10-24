"""Recompute genuine OOF metrics from canonical harness OOF files.

Convention (experiment_harness.py): Brier = mean over OOF rows of
sum_k (p_k - t_k)^2 over classes [0=Away, 1=Draw, 2=Home]; range [0, 2].
"""
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

FILES = {
    "baseline_roll_ref (current 6399-row data, canonical OOF)":
        "experiments/oof_baseline_roll_ref_20261010T150337Z.csv",
    "roll_w5_w10 (Phase 1.2 candidate, canonical OOF)":
        "experiments/oof_roll_w5_w10_20261010T150442Z.csv",
}


def main():
    rows = []
    for label, path in FILES.items():
        df = pd.read_csv(path)
        y = df["y_true"].astype(int).values
        P = df[["p_away", "p_draw", "p_home"]].values
        onehot = np.eye(3)[y]
        brier = float(np.mean(np.sum((P - onehot) ** 2, axis=1)))
        ll = float(log_loss(y, P, labels=[0, 1, 2]))
        pred = P.argmax(axis=1)
        acc = float(accuracy_score(y, pred))
        draw_pred = int((pred == 1).sum())
        draw_recall = float((pred[y == 1] == 1).mean())
        rows.append((label, len(df), acc, ll, brier, draw_pred, draw_recall))

    print(f"{'run':55s} {'n':>6s} {'acc':>7s} {'LL':>7s} {'Brier':>7s} {'nDraw':>6s} {'drawRec':>8s}")
    for label, n, acc, ll, brier, nd, dr in rows:
        print(f"{label:55s} {n:6d} {acc:7.4f} {ll:7.4f} {brier:7.4f} {nd:6d} {dr:8.4f}")

    print("\nReference points:")
    print("  phase14 'baseline' Brier 0.5448  <- computed IN-SAMPLE (model trained on all rows")
    print("     via run_pipeline(), then used to predict the same rows it trained on)")
    print("  phase14 'candidate' Brier 0.6551 <- computed OOF (fresh model per fold)")
    print("  => Phase 1.4 Brier delta +0.1103 (+20.2%) compared IN-SAMPLE vs OOF: INVALID")


if __name__ == "__main__":
    sys.exit(main())
