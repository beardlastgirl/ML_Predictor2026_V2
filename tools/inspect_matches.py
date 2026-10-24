"""Deterministic same-day / duplicate-date inspection for data/ARG.csv.

Never trust an AI to 'look at' the CSV. This produces the numbers both AIs cite.
Output: <out>/duplicate_dates.json and <out>/match_report.txt
"""
import argparse, json, pathlib
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="data/ARG.csv")
ap.add_argument("--out", required=True)
a = ap.parse_args()

df = pd.read_csv(a.csv)
out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
report = {}

# --- schema discovery (football-data.co.uk format can drift between seasons)
date_col = next((c for c in df.columns if c.strip().lower() == "date"), None)
time_cols = [c for c in df.columns if "time" in c.lower()]
report["columns"] = list(df.columns)
report["date_column"] = date_col
report["time_columns"] = time_cols

if date_col is None:
    raise SystemExit("No Date column found; columns were: " + ", ".join(df.columns))

dates = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
report["unparseable_dates"] = int(dates.isna().sum())
df["_date"] = dates

# --- same-day analysis
counts = df.dropna(subset=["_date"]).groupby("_date").size()
multi = counts[counts > 1]
report["total_rows"] = len(df)
report["date_range"] = [str(dates.min().date()), str(dates.max().date())]
report["unique_dates"] = int(counts.size)
report["dates_with_multiple_matches"] = int(multi.size)
report["max_matches_on_one_date"] = int(counts.max())
report["dates_with_3plus_matches"] = int((counts >= 3).sum())
report["top_duplicate_dates"] = [
    {"date": str(d.date()), "matches": int(n)}
    for d, n in multi.sort_values(ascending=False).head(10).items()]

# --- kickoff time availability
time_report = {}
for tc in time_cols:
    s = df[tc].astype(str).str.strip()
    nonempty = (s != "") & (s.str.lower() != "nan")
    looks_like_time = s.str.match(r"^\d{1,2}[:.]\d{2}", na=False)
    time_report[tc] = {
        "nonempty_fraction": round(float(nonempty.mean()), 4),
        "parseable_time_fraction": round(float(looks_like_time.mean()), 4),
    }
report["time_quality"] = time_report
has_usable_time = any(t["nonempty_fraction"] > 0.5 for t in time_report.values())
report["intra_day_ordering_possible"] = bool(has_usable_time)

# --- season distribution (for the CV/warmup jobs later)
season_col = next((c for c in df.columns if "season" in c.lower() or c.strip() in ("Sea", "Season")), None)
if season_col:
    report["rows_by_season_head"] = df[season_col].value_counts().head(15).to_dict()

# --- examples of duplicate dates (trimmed rows)
examples = {}
for d in multi.sort_values(ascending=False).head(5).index:
    cols = [c for c in [date_col] + time_cols +
            [x for x in ("Home", "Away", "FTHG", "FTAG", "FTR", "Season", "Div") if x in df.columns]]
    examples[str(d.date())] = df.loc[df["_date"] == d, cols].head(8).to_dict(orient="records")
report["duplicate_date_examples"] = examples

verdict = ("Kickoff times are largely ABSENT/UNRELIABLE -> intra-day match order is UNKNOWN. "
           "Any pipeline using features from 'previous matches' must define an explicit deterministic "
           "tiebreak for same-date matches, and audits must not treat same-date rows as ordered."
           if not has_usable_time else
           "Kickoff times look mostly present -> intra-day ordering may be possible; verify parse quality.")
report["ordering_verdict"] = verdict

(out / "duplicate_dates.json").write_text(json.dumps(report, indent=2, default=str))
lines = [f"rows={report['total_rows']}  dates={report['unique_dates']}  "
         f"dup_dates={report['dates_with_multiple_matches']}  "
         f"max_on_one_date={report['max_matches_on_one_date']}",
         f"date_col={date_col}  time_cols={time_cols}  "
         f"intra_day_ordering_possible={report['intra_day_ordering_possible']}",
         "", verdict, "",
         "Top duplicate dates:"]
lines += [f"  {e['date']}: {e['matches']} matches" for e in report["top_duplicate_dates"]]
(out / "match_report.txt").write_text("\n".join(lines))
print("\n".join(lines))
