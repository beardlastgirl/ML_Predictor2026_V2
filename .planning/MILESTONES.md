# Milestone History

## Apertura 2026 — Season Complete (Current)

**Status:** Regular season done (Fecha 9). Playoffs pending.

**Delivered this season:**
- ✅ Scoreline bug fixed (all-1-1 → varied realistic scores)
- ✅ GF/GA column mapping corrected
- ✅ Season-start new-team detection
- ✅ Poisson calibration utility (`calibrate_poisson_params`)
- ✅ `scrape_tyc.py` generalized (no hardcoded season data)
- ✅ Glossary updated (Boca, Independiente Rivadavia Mza variants)
- ✅ 34 tests passing
- ✅ Documentation updated, 7 obsolete files deleted

---

## v2.0 — Initialization & Alignment (Completed 2026-04-24)

- ✅ DATA-01: Betting odds integrated as Shin method features
- ✅ DATA-02: Time-series CV prevents data leakage
- ✅ MODEL-01: Naive + bookie baseline comparison in output

---

## v1.0 — Production Quality & Fixes (Completed 2026-03-21)

- ✅ 10 priority bugs fixed (3 critical, 5 high, 2 medium)
- ✅ Data validation layer (`src/validation.py`)
- ✅ Scraper resilience (`src/scraper_utils.py`)
- ✅ 26/26 tests passing at release
