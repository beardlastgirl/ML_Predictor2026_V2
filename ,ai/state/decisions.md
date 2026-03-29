# .ai/state/decisions.md
# Architecture Decision Records

---

## ADR-001 — Replace Codex with Claude Code as primary orchestrator
**Date:** 2026-03-27
**Status:** Accepted

**Context:**
Codex config contained hardcoded absolute paths (`C:/Scripts/...` vs actual `I:/Scripts/...`),
causing reliability failures. Framework was duplicated across `.codex`, `.claude`, `.gemini`,
`.agent`, `.opencode`, and `.github` — 900+ config files and ~8 MB of payload before real work.

**Decision:**
Claude Code is the single orchestrator. All config lives in `.claude/config.toml` and `AGENTS.md`.
Retired directories are archived, not deleted.

**Consequences:**
- Cold start reads one file (AGENTS.md) instead of multiple docs.
- No absolute paths anywhere in config.
- MCP is opt-in per task class, not global.
- Hook count reduced to zero (add back only when measurably needed).

---

## ADR-002 — Reduce agent roster from 16+ to 3 specialist roles
**Date:** 2026-03-27
**Status:** Accepted

**Context:**
Agents included roadmapper, phase researcher, plan checker, research synthesizer,
integration checker, nyquist auditor, user profiler, and others — overlapping bureaucracy
that cost tokens without producing distinct value.

**Decision:**
Three roles only: planner, debugger, reviewer.
Each has a narrow trigger condition and a structured output format.

---

## ADR-003 — Remove colab-mcp and roundtable from default MCP config
**Date:** 2026-03-27
**Status:** Accepted

**Context:**
Both servers were enabled by default with no demonstrated use case for a local Python pipeline.

**Decision:**
Removed. Playwright kept but scoped to `scraper-maintenance` task class only.
Rule: MCP servers must be justified by a specific, recurring task class before enabling.
