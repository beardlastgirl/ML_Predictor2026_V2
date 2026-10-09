"""Phase 1.0 experiment harness — infrastructure only, no model changes.

Runs one experiment through the production path (load_data -> build_features ->
5-fold TimeSeriesSplit CV) and appends a complete record to
experiments/results.jsonl. A later variant ships only if its 3-class log loss /
Brier improves out-of-sample on the SAME folds as the frozen baseline
(acc 0.4324 / LL 1.1028 / Brier 0.6662, see PHASE0_2_Temporal_Integrity_Report.md).

Usage:
    python -m src.experiment_harness --name baseline_verify_1
    python -m src.experiment_harness --name baseline_verify_1 --model catboost

Fold loop mirrors pipeline.train_validate exactly (same TimeSeriesSplit(5),
same draw sample weight 0.7, same create_model params); it is duplicated here
only because train_validate does not expose fold boundaries or out-of-fold
predictions, which the experiment record requires.

Brier convention: multiclass summed-squared-error over classes [0=Away,
1=Draw, 2=Home], averaged over out-of-fold rows (range [0, 2]).
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss
from sklearn.model_selection import TimeSeriesSplit

from src.config import MODEL_TYPE
from src.model_engine import create_model
from src.pipeline import FEATURE_COLUMNS, build_features, load_data

RESULTS_LOG = Path("experiments/results.jsonl")
N_SPLITS = 5
DRAW_WEIGHT = 0.7
CLASSES = [0, 1, 2]  # 0=Away, 1=Draw, 2=Home
BRIER_CONVENTION = "multiclass_sse_mean_over_oof_rows_range_0_2"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _environment() -> dict:
    import catboost
    import lightgbm
    import sklearn

    return {
        "python": platform.python_version(),
        "os": platform.system(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sklearn": sklearn.__version__,
        "catboost": catboost.__version__,
        "lightgbm": lightgbm.__version__,
    }


def run_experiment(
    name: str,
    model_type: str = MODEL_TYPE,
    features: list = None,
    notes: str = "",
    historical_path: str = "data/ARG.csv",
) -> dict:
    """Run one experiment on the frozen evaluation methodology and log it."""
    features = list(features) if features else list(FEATURE_COLUMNS)
    record = {
        "experiment_id": f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "name": name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "notes": notes,
        "config": {
            "model_type": model_type,
            "features": features,
            "n_features": len(features),
            "n_splits": N_SPLITS,
            "splitter": "TimeSeriesSplit",
            "draw_sample_weight": DRAW_WEIGHT,
            "class_order": {"0": "Away", "1": "Draw", "2": "Home"},
            "brier_convention": BRIER_CONVENTION,
        },
        "data": {},
        "environment": _environment(),
        "folds": [],
        "aggregate": {},
        "error": None,
    }
    try:
        record["data"] = {
            "historical_path": historical_path,
            "historical_sha256": _sha256_file(historical_path),
        }
        _, _, matches, _ = load_data(historical_path=historical_path)
        matches_feat, _ = build_features(matches)
        df = matches_feat.dropna(subset=FEATURE_COLUMNS).copy()
        X, y = df[features], df["Res"]
        sample_weights = np.where(y.values == 1, DRAW_WEIGHT, 1.0)
        record["data"].update(
            {"rows_raw": len(matches), "rows_eligible": len(df)}
        )

        tscv = TimeSeriesSplit(n_splits=N_SPLITS)
        oof_proba = np.full((len(X), len(CLASSES)), np.nan)
        oof_pred = np.full(len(X), -1)
        for fold, (t_idx, v_idx) in enumerate(tscv.split(X), 1):
            model = create_model(model_type)
            model.fit(X.iloc[t_idx], y.iloc[t_idx], sample_weight=sample_weights[t_idx])
            proba = model.predict_proba(X.iloc[v_idx])
            pred = np.asarray(model.predict(X.iloc[v_idx])).ravel()
            oof_proba[v_idx] = proba
            oof_pred[v_idx] = pred
            d_train, d_val = df.iloc[t_idx]["Date"], df.iloc[v_idx]["Date"]
            record["folds"].append(
                {
                    "fold": fold,
                    "train_n": int(len(t_idx)),
                    "val_n": int(len(v_idx)),
                    "train_date_range": [str(d_train.min().date()), str(d_train.max().date())],
                    "val_date_range": [str(d_val.min().date()), str(d_val.max().date())],
                    "val_index_range": [int(v_idx[0]), int(v_idx[-1])],
                    "accuracy": float(accuracy_score(y.iloc[v_idx], pred)),
                    "log_loss": float(log_loss(y.iloc[v_idx], proba)),
                }
            )

        mask = oof_pred >= 0
        y_oof = y.values[mask].astype(int)
        onehot = np.eye(len(CLASSES))[y_oof]
        accs = [f["accuracy"] for f in record["folds"]]
        lls = [f["log_loss"] for f in record["folds"]]
        record["aggregate"] = {
            "oof_n": int(mask.sum()),
            "mean_accuracy": float(np.mean(accs)),
            "std_accuracy": float(np.std(accs)),
            "mean_log_loss": float(np.mean(lls)),
            "std_log_loss": float(np.std(lls)),
            "brier_multiclass": float(
                np.mean(np.sum((oof_proba[mask] - onehot) ** 2, axis=1))
            ),
            "oof_accuracy": float(accuracy_score(y_oof, oof_pred[mask])),
            "confusion_matrix_oof": confusion_matrix(
                y_oof, oof_pred[mask], labels=CLASSES
            ).tolist(),
        }
    except Exception:
        record["error"] = traceback.format_exc()

    RESULTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 experiment harness")
    parser.add_argument("--name", required=True, help="Experiment name")
    parser.add_argument("--model", default=MODEL_TYPE, choices=["catboost", "lightgbm"])
    parser.add_argument(
        "--features",
        default=None,
        help="Comma-separated feature subset (default: all 24 FEATURE_COLUMNS)",
    )
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    features = args.features.split(",") if args.features else None
    record = run_experiment(args.name, args.model, features, args.notes)

    if record["error"]:
        print(f"[ERROR] Experiment {record['experiment_id']} failed:")
        print(record["error"])
        return 1

    agg = record["aggregate"]
    print(f"[OK] {record['experiment_id']}")
    for f in record["folds"]:
        print(
            f"  Fold {f['fold']}: train={f['train_n']} {f['train_date_range']}, "
            f"val={f['val_n']} {f['val_date_range']}, "
            f"acc={f['accuracy']:.4f}, ll={f['log_loss']:.4f}"
        )
    print(
        f"  Mean acc={agg['mean_accuracy']:.4f} (+/- {agg['std_accuracy']:.4f}), "
        f"mean ll={agg['mean_log_loss']:.4f} (+/- {agg['std_log_loss']:.4f}), "
        f"brier={agg['brier_multiclass']:.4f}, oof_n={agg['oof_n']}"
    )
    print(f"  Logged to {RESULTS_LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
