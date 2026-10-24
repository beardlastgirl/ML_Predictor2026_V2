"""Print aggregate metrics from experiments/results.jsonl."""
import json

PATH = "experiments/results.jsonl"

with open(PATH, "r", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r.get("error"):
            print(f"{r['name']}: ERROR")
            continue
        a = r["aggregate"]
        print(
            f"{r['name']:20s} nfeat={r['config']['n_features']:3d} "
            f"acc={a['mean_accuracy']:.4f}+-{a['std_accuracy']:.4f} "
            f"ll={a['mean_log_loss']:.4f}+-{a['std_log_loss']:.4f} "
            f"brier={a['brier_multiclass']:.4f} oof_n={a['oof_n']}"
        )
        print("    fold ll :", " ".join(f"{f['log_loss']:.4f}" for f in r["folds"]))
        print("    fold acc:", " ".join(f"{f['accuracy']:.4f}" for f in r["folds"]))
