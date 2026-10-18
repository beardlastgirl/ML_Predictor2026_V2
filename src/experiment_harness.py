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

from src.config import MODEL_TYPE, ROLLING_WINDOW_CANDIDATES
from src.model_engine import create_model
from src.pipeline import FEATURE_COLUMNS, build_features, load_data

RESULTS_LOG = Path("experiments/results.jsonl")
OOF_DIR = Path("experiments")
N_SPLITS = 5
DRAW_WEIGHT = 0.7
CLASSES = [0, 1, 2]  # 0=Away, 1=Draw, 2=Home
BRIER_CONVENTION = "multiclass_sse_mean_over_oof_rows_range_0_2"

# Phase 1.1 sporting-form variants. Small a priori candidate set; no tuning
# beyond these values (see config.EWMA_HALFLIFE_CANDIDATES).
# Phase 1.2 rolling-window candidate set (windows from
# config.ROLLING_WINDOW_CANDIDATES; a priori, no further tuning).
ROLL_FEATURES = [
    f"{side}_Roll{w}_{stat}"
    for w in ROLLING_WINDOW_CANDIDATES
    for side in ("Home", "Away")
    for stat in ("Form", "GD")
]
VARIANTS = {
    "ewma_hl2": ({"type": "ewma", "halflife": 2},
                 ["Home_EWMA_Form", "Home_EWMA_GF", "Home_EWMA_GA",
                  "Away_EWMA_Form", "Away_EWMA_GF", "Away_EWMA_GA"]),
    "ewma_hl4": ({"type": "ewma", "halflife": 4},
                 ["Home_EWMA_Form", "Home_EWMA_GF", "Home_EWMA_GA",
                  "Away_EWMA_Form", "Away_EWMA_GF", "Away_EWMA_GA"]),
    "ewma_hl8": ({"type": "ewma", "halflife": 8},
                 ["Home_EWMA_Form", "Home_EWMA_GF", "Home_EWMA_GA",
                  "Away_EWMA_Form", "Away_EWMA_GF", "Away_EWMA_GA"]),
    "venue_split": ({"type": "venue_split"},
                    ["Home_Venue_Form", "Home_Venue_GF", "Home_Venue_GA",
                     "Away_Venue_Form", "Away_Venue_GF", "Away_Venue_GA"]),
    "roll_windows": ({"type": "multi_window", "windows": list(ROLLING_WINDOW_CANDIDATES)},
                     ROLL_FEATURES),
}


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
    variant: str = None,
) -> dict:
    """Run one experiment on the frozen evaluation methodology and log it."""
    form_variant = None
    variant_features = []
    if variant:
        if variant not in VARIANTS:
            raise ValueError(f"Unknown variant '{variant}'. Known: {sorted(VARIANTS)}")
        form_variant, variant_features = VARIANTS[variant]
        if features:
            raise ValueError("--features and --variant are mutually exclusive")

    features = list(features) if features else list(FEATURE_COLUMNS) + variant_features
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
            "form_variant": form_variant,
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
        matches_feat, _ = build_features(matches, form_variant=form_variant)
        df = matches_feat.dropna(subset=FEATURE_COLUMNS).copy()
        # Variant features must not change the eligible/OOF row sets; they are
        # NaN only where baseline trailing features are NaN (documented in
        # batched_features). Fail loudly rather than silently changing folds.
        n_variant_nan = int(df[variant_features].isna().any(axis=1).sum()) if variant_features else 0
        if n_variant_nan:
            raise ValueError(
                f"Variant '{variant}' introduced NaN in {n_variant_nan} eligible rows; "
                "OOF set would differ from baseline. Fix the variant's fallback."
            )
        record["data"].update(
            {"rows_raw": len(matches), "rows_eligible": len(df),
             "rows_with_variant_nan": n_variant_nan}
        )

        tscv = TimeSeriesSplit(n_splits=N_SPLITS)
        oof_proba = np.full((len(X := df[features]), len(CLASSES)), np.nan)
        oof_pred = np.full(len(X), -1)
        oof_fold = np.full(len(X), -1)
        y = df["Res"]
        sample_weights = np.where(y.values == 1, DRAW_WEIGHT, 1.0)
        for fold, (t_idx, v_idx) in enumerate(tscv.split(X), 1):
            model = create_model(model_type)
            model.fit(X.iloc[t_idx], y.iloc[t_idx], sample_weight=sample_weights[t_idx])
            proba = model.predict_proba(X.iloc[v_idx])
            pred = np.asarray(model.predict(X.iloc[v_idx])).ravel()
            oof_proba[v_idx] = proba
            oof_pred[v_idx] = pred
            oof_fold[v_idx] = fold
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

        # Per-match OOF probabilities for paired uncertainty analysis
        oof_df = pd.DataFrame(
            {
                "pos": np.where(mask)[0],
                "fold": oof_fold[mask].astype(int),
                "y_true": y_oof,
                "p_away": oof_proba[mask, 0],
                "p_draw": oof_proba[mask, 1],
                "p_home": oof_proba[mask, 2],
            }
        )
        oof_path = OOF_DIR / f"oof_{record['experiment_id']}.csv"
        oof_df.to_csv(oof_path, index=False)
        record["oof_file"] = str(oof_path)
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
    parser.add_argument(
        "--variant",
        default=None,
        choices=sorted(VARIANTS),
        help="Sporting-form variant; appends its features to the 24 base features",
    )
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    features = args.features.split(",") if args.features else None
    record = run_experiment(args.name, args.model, features, args.notes, variant=args.variant)

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
