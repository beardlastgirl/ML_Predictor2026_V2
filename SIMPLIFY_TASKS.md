# Simplify Tasks — Commit f0adef4

## HIGH Priority

- [x] Consolidate duplicate name normalization (`data_processing.py:10` vs `data_ingestion.py:34`)
- [x] Consolidate duplicate team mappings (`data_ingestion.py:20-31` vs `data_processing.py:106-144`) — Added clarifying comment, maps serve different purposes
- [ ] Replace iterrows() with vectorized ops (`features.py:99-108`) — DEFERRED: significant refactor
- [x] Move column apply outside loop (`data_ingestion.py:314-315`)

## MEDIUM Priority

- [ ] Flatten nested conditionals in `_calculate_hybrid_goals` (`model_engine.py:58-74`) — DEFERRED: changes logic
- [x] Replace magic number 0.6 with config reference (`model_engine.py:131`)
- [x] Move imports to module level (`model_engine.py:558`)
- [ ] Remove redundant verbose comments in config.py — DEFERRED: low value
- [x] Use iloc instead of loc with index (`pipeline.py:293`) — SKIP: preserves original index intentionally
- [ ] Vectorize calibrate_poisson_params loop (`stats_engine.py:949-952`) — DEFERRED: complex

## LOW Priority

- [ ] Remove unused `_internal_mapping_raw` after INTERNAL_MAPPING built
- [ ] Consolidate import ordering in data_ingestion.py
- [ ] Fix inefficient probability extraction in pipeline.py