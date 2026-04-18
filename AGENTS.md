# AGENTS.md
# ML_Predictor2026_V2 — Agent Operating Manual

## Orchestrator: Gemini CLI

Default behavior: **solve directly with minimal context.**
- Reads only AGENTS.md and task-relevant files on startup.
- Use one skill only when the task class matches.
- Spawn a subagent only for `planner`, `debugger`, or `reviewer` roles.
- Persist only decisions, next step, and blockers to `.ai/state/current.md`.
- Never require reading large docs before writing code.

---

## Agent Roster (3 specialist roles only)

| Agent      | When to spawn                                      | Output                                          |
|------------|----------------------------------------------------|-------------------------------------------------|
| planner    | Ambiguous work or task spanning 3+ files           | Scoped plan, file list, verification command    |
| debugger   | Failing test, crash, or scraper breakage is reproducible | Root cause, minimal patch plan, verify cmd |
| code-reviewer   | After implementation only — read-only              | Findings list, no code changes                  |

**Adhere to the 3 specialist roles only.**

---

## Skill Loading (lazy, from global `.agents/skills/` or project-specific `.gemini/skills/`)

Load at most **one skill per task**. Match by task class:

| Task class            | Skill                    |
|-----------------------|--------------------------|
| Model training / eval | `prediction-pipeline`    |
| Scraper failures      | `scraper-maintenance`    |
| Data cleaning         | `data-normalization`     |
| Release / changelog   | `release-review`         |
| Code Review           | `code-reviewer`          |

---

## State Layer (single source of truth)

```
.ai/
  state/
    current.md    ← active task, next step, blockers
    backlog.md    ← queued work items
    decisions.md  ← architecture decisions with rationale
AGENTS.md         ← this file (agent config)
ARCHITECTURE.md   ← system overview
.gemini/
  config.toml     ← MCP servers, skill/agent config
  agents/         ← subagent definitions
  skills/         ← lazy-loaded skill files
```

Store **conclusions**, not transcripts.
DEV_CONTEXT and CONTEXT_SUMMARY.md are retired — use `.ai/state/` only.
