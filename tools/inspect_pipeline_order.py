"""Deterministic inspection of sort/order/window/split operations in pipeline files.

AST-based: reports WHERE rolling/EWMA windows, sorts, merges and splits happen,
so leakage discussions cite lines instead of vibes.
Output: <out>/pipeline_order.json and <out>/pipeline_order_report.txt
"""
import argparse, ast, json, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("--files", nargs="+", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
INTERESTING = {"sort_values", "rolling", "ewm", "shift", "merge", "concat",
               "train_test_split", "TimeSeriesSplit", "fit", "fit_transform",
               "groupby", "dropna", "sample"}
results = {}
for f in a.files:
    src = pathlib.Path(f).read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    hits, defs = [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.append({"name": node.name, "line": node.lineno})
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in INTERESTING:
                kw = [k.arg for k in node.keywords]
                hits.append({"call": name, "line": node.lineno, "kwargs": kw})
    hits.sort(key=lambda h: h["line"])
    results[f] = {"functions": sorted(defs, key=lambda d: d["line"]), "calls": hits}

# cross-file ordering of the load -> features -> split -> train flow
flow_flags = {
    "explicit_sort_before_features": None,
    "shift_used_anywhere": None,
    "ewm_used_anywhere": None,
    "split_call_seen": None,
}
all_hits = [h for r in results.values() for h in r["calls"]]
flow_flags["shift_used_anywhere"] = any(h["call"] == "shift" for h in all_hits)
flow_flags["ewm_used_anywhere"] = any(h["call"] == "ewm" for h in all_hits)
flow_flags["split_call_seen"] = any("split" in h["call"].lower() for h in all_hits)

(out / "pipeline_order.json").write_text(
    json.dumps({"per_file": results, "flow_flags": flow_flags}, indent=2))

lines = [f"flow flags: {flow_flags}", ""]
for f, r in results.items():
    lines.append(f"== {f} ==")
    lines.append("  functions: " + ", ".join(f"{d['name']}@{d['line']}" for d in r["functions"]))
    for h in r["calls"]:
        lines.append(f"  L{h['line']:>4}  {h['call']}({', '.join(h['kwargs'])})")
    lines.append("")
(out / "pipeline_order_report.txt").write_text("\n".join(lines))
print("\n".join(lines[:40]))
