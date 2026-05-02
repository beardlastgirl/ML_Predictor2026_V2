# BUG_TRACKING.md

**Last Updated:** 2026-05-02

## Active Issues

None currently blocking.

---

## Resolved Bugs

### B001 — json import missing (2026-02-27) ✅
- `load_sofascore_data()` used `json.load()` without importing json
- Fix: Added `import json`

### B002 — Sofascore Apify format mismatch (2026-02-27) ✅
- `load_sofascore_data()` only handled manual JSON format
- Fix: Updated to detect and parse both Apify nested format and manual flat format

### B003 — All scores 2-1 or 1-2 (2026-02-27) ✅
- Score generation forced home/away wins regardless of Poisson probabilities
- Fix: Rewrote to use Poisson most-likely scoreline with confidence threshold

### B004 — Prediction_Label mismatch (2026-02-27) ✅
- Label derived from ML prediction, not actual predicted goals
- Fix: Derive label from `Pred_Home_Goals` vs `Pred_Away_Goals`

### CR-001 — Division by zero in form calculation ✅
- `form = points / len(recent)` with empty history
- Fix: Guard clause `if len(recent) > 0 else np.nan`

### CR-002 — Integer conversion without bounds ✅
- `int(row["Pred_Home_Goals"])` crashes on NaN/Inf
- Fix: `int(np.clip(row.get("Pred_Home_Goals", 0), 0, 6))`

### CR-003 — Probability normalization zero denominator ✅
- Division by zero if total probability = 0
- Fix: Fallback to uniform 1/3 distribution when total < 1e-10

### CR-004 — Matplotlib memory leak ✅
- `plt.close(fig)` not reached on exception
- Fix: `try/finally` block ensures cleanup

### CR-005 — Elo diff bug ✅
- `elo_diff = elo_home - elo_home` (typo)
- Fix: `elo_diff = elo_home - elo_away`

### B005 — All scores 1-1 (2026-05-02) ✅
- **Root cause 1:** `_calculate_hybrid_goals` used `round(xG)` — Liga Profesional xG values (0.8–1.6) all round to 1
- **Root cause 2:** ML adjustment threshold `ml_weight > 0.3` unreachable — scaled weight always 0.21–0.27
- **Root cause 3:** `get_all_teams_latest_stats` read `GF`/`GA` as zeros when `Home_GF`/`Away_GF` columns were present
- Fix: `floor(xG)` as base; `max_prob >= 0.35` direct threshold; `Home_GF`/`Away_GF` fallback

### B006 — GF/GA column mapping bug (2026-05-02) ✅
- `pipeline.py` assigned `Away_GF` to `GA` via wrong variable name in comment
- Fix: Explicit `matches["GF"] = matches["Home_GF"]`, `matches["GA"] = matches["Away_GF"]` with FTHG/FTAG fallback

### B007 — `enrich_with_api_stats` silent stub (2026-05-02) ✅
- Function fetched from API then did nothing, logging misleading "completed" message
- Fix: Replaced with explicit no-op log: "skipped (team name mapping not yet implemented)"

### B008 — `scrape_tyc.py` hardcoded to old season (2026-05-02) ✅
- Hardcoded URL pointing to Clausura 2025 fixture page
- Hardcoded Fecha 6 team list
- Fix: Removed hardcoded data; `--url` and `--fecha` CLI args; generic DOM parser

### B009 — Boca / Independiente Rivadavia Mza not recognized (2026-05-02) ✅
- `Partidos.txt` uses "Boca" and "Independiente Rivadavia Mza." — neither matched glossary
- Fix: Added `Boca -> BOCA JUNIORS` and `Independiente Rivadavia Mza -> IND RIVADAVIA` variants to `Glossary.txt`

---

## Known Limitations (Not Bugs)

- ML accuracy ~35% on 3-class problem (near-random). Expected for this domain.
- Playoffs not modeled — trained on regular season data only.
- `enrich_with_api_stats` is a no-op pending team name mapping implementation.
- TyC scraper requires manual URL update each season.
