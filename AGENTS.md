# AGENTS.md
# ML_Predictor2026_V2 — Agent Operating Manual

## Orchestrator: Claude Code

Default behavior: **solve directly with minimal context.**
- Reads CLAUDE.md and task-relevant files on startup.
- Use one skill only when the task class matches.
- Spawn a subagent only for `planner`, `debugger`, or `reviewer` roles.
- Persist only decisions, next step, and blockers to ContextVault.
- Never require reading large docs before writing code.

---

## Agent Roster (3 specialist roles only)

| Agent      | When to spawn                                      | Output                                          |
|------------|----------------------------------------------------|-------------------------------------------------|
| planner    | Ambiguous work or task spanning 3+ files           | Scoped plan, file list, verification command    |
| debugger   | Failing test, crash, or scraper breakage is reproducible | Root cause, minimal patch plan, verify cmd |
| code-reviewer   | After implementation only — read-only              | Findings list, no code changes                  |

---

## Skill Loading (lazy, from .claude/skills/)

Load at most **one skill per task**. Match by task class:

| Task class            | Skill                    |
|-----------------------|--------------------------|
| Model training / eval | `footballbin-predictions`|
| Scraper failures      | `browser-automation`     |
| Data cleaning         | `liga-argentina-predictions-api` |
| Code Review           | `code-reviewer`          |

---

## State Layer

```
.claude/
  settings.json           ← MCP + hook config
  skills/                 ← lazy-loaded skill files
  agents/                ← subagent definitions
  vault/                 ← ContextVault documentation

.ai/
  state/
    current.md           ← active task, next step, blockers
    decisions.md         ← architecture decisions with rationale
```

Store **conclusions**, not transcripts.