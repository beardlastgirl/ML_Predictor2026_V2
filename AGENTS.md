# AGENTS.md
# ML_Predictor2026_V2 — Agent Operating Manual

## Orchestrator: Claude Code

Default behavior: **solve directly with minimal context.**
- Read only AGENTS.md and task-relevant files on startup.
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
| reviewer   | After implementation only — read-only              | Findings list, no code changes                  |

**Do not create:** roadmapper, phase researcher, plan checker, research synthesizer,
integration checker, nyquist auditor, user profiler, or any other single-thought-role agent.

---

## Skill Loading (lazy, from `.claude/skills/`)

Load at most **one skill per task**. Match by task class:

| Task class            | Skill                    |
|-----------------------|--------------------------|
| Model training / eval | `prediction-pipeline`    |
| Scraper failures      | `scraper-maintenance`    |
| Data cleaning         | `data-normalization`     |
| Release / changelog   | `release-review`         |

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
.claude/
  config.toml     ← MCP servers, hook config
  agents/         ← subagent definitions
  skills/         ← lazy-loaded skill files
```

Store **conclusions**, not transcripts.
DEV_CONTEXT and CONTEXT_SUMMARY.md are retired — use `.ai/state/` only.
