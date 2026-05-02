# Architecture Decision Records

## ADR-001 — Claude Code as single orchestrator (2026-03-27)
**Status:** Accepted

Replaced fragmented multi-framework setup (Codex, Gemini, OpenCode) with Claude Code as sole orchestrator. All config in `AGENTS.md` and `CLAUDE.md`. Three specialist roles only: planner, debugger, code-reviewer.

## ADR-002 — Reduce agent roster to 3 roles (2026-03-27)
**Status:** Accepted

Eliminated 16+ overlapping agent roles. Kept: planner (ambiguous multi-file tasks), debugger (reproducible failures), code-reviewer (post-implementation, read-only).

## ADR-003 — MCP opt-in per task class (2026-03-27)
**Status:** Accepted

Removed colab-mcp and roundtable from default config. Playwright kept but scoped to scraper-maintenance only.

## ADR-004 — floor(xG) for scoreline base (2026-05-02)
**Status:** Accepted

`round(xG)` collapsed all Liga Profesional xG values (0.8–1.6) to 1, producing all-1-1 scores. `floor(xG)` is the Poisson mode and gives realistic spread (0 for weak teams, 1 for average).

## ADR-005 — Direct probability threshold for ML adjustment (2026-05-02)
**Status:** Accepted

Previous approach: `ml_weight = max_prob * 0.6 > 0.3` — unreachable with typical blended probabilities (0.35–0.45). New approach: `max_prob >= 0.35` direct check. ML directional adjustment now fires correctly.

## ADR-006 — BASE_GOAL_RATE as NaN fallback only (2026-05-02)
**Status:** Accepted

`BASE_GOAL_RATE` is not a scaling factor in the xG formula. It is only used as the fallback value when a team has no trailing stats (e.g. promoted teams at season start). Clarified in config.py and SYSTEM_KNOWLEDGE.md.
