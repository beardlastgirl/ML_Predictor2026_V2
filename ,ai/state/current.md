# Current Task State

**Last Updated:** 2026-05-02

## Status
idle — Apertura 2026 regular season complete (Fecha 9). Playoffs pending (structure TBD).

## Last Actions
- Fixed all-1-1 scoreline bug (floor(xG), ML threshold, GF/GA fallback)
- Fixed scrape_tyc.py hardcoded season data
- Added Boca / Independiente Rivadavia Mza to Glossary.txt
- Updated all MD documentation, deleted 7 obsolete files

## Next Step
When playoff fixtures are known: update Partidos.txt and run `python main.py`.
Consider running `calibrate_poisson_params()` before next season.

## Blockers
None. Waiting on Argentine football to decide playoff format.
