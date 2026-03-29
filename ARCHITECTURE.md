# ARCHITECTURE.md
# ML_Predictor2026_V2 — System Architecture

## Orchestration Model

```
User request
  └─> Claude Code (Orchestrator)
        ├─ classify: code / debug / review / docs / scraper
        ├─ load 1 skill max (lazy from .claude/skills/)
        ├─ do work directly unless blocked
        ├─ spawn one bounded subagent only if task is parallelizable
        ├─ verify output
        └─ write minimal state snapshot to .ai/state/current.md
```

**Default: single-agent.** Multi-agent only when a task is genuinely parallelizable.

---

## Directory Layout

```
I:\Scripts\ML_Predictor2026_V2\
├── AGENTS.md                  ← agent roster and operating rules
├── ARCHITECTURE.md            ← this file
├── .ai\
│   └── state\
│       ├── current.md         ← active task, next step, blockers
│       ├── backlog.md         ← queued items
│       └── decisions.md       ← ADRs (architecture decision records)
└── .claude\
    ├── config.toml            ← MCP + hook config (no absolute paths)
    ├── agents\
    │   ├── planner.md
    │   ├── debugger.md
    │   └── reviewer.md
    └── skills\
        ├── prediction-pipeline\SKILL.md
        ├── scraper-maintenance\SKILL.md
        ├── data-normalization\SKILL.md
        └── release-review\SKILL.md
```

### Retired / Archived

The following directories should be archived (not deleted) and removed from active agent context:

- `.agent/`
- `.gemini/`
- `.opencode/`
- `.github/get-shit-done/`
- `.github/agents/`
- `.github/skills/`
- `CONTEXT_SUMMARY.md`
- `.planning/` (most of it)

---

## Design Principles

1. **Single source of truth.** Config lives in `.claude/config.toml` and `AGENTS.md` only.
2. **Store conclusions, not transcripts.** `.ai/state/` holds decisions and next steps — not conversation logs.
3. **No startup ritual.** Claude Code reads `AGENTS.md` and the task-relevant file(s). Nothing else on cold start.
4. **Opt-in MCP.** Servers are enabled per task class, not globally.
5. **No session-wide hooks.** No `PostToolUse` or `AfterTool` context monitors.
