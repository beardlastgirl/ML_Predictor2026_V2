# Two-AI Orchestrator Kit for ML_Predictor2026_V2

AI#1 = Claude Code or Codex CLI (orchestrator, edits files, final authority)
AI#2 = local Ollama model (read-only critic, consulted EXACTLY ONCE per job)

## Install
1. Copy this kit into the repo root (same level as main.py, src/, data/).
2. Ensure all three CLIs are on PATH: `claude --version`, `codex --version`, `ollama --version`
3. `ollama pull qwen2.5-coder:7b`

## Run (PowerShell)
```powershell
$env:ENGINE = "claude"            # or "codex"
$env:CRITIC_MODEL = "qwen2.5-coder:7b"
$env:STOP_BETWEEN_JOBS = "1"      # set "0" only for unattended overnight runs
python orchestrate.py
```

## What happens per job
1. Deterministic runner tools produce evidence in `jobs/<id>/runner_output/` (AIs never guess file contents)
2. Baseline pytest run recorded
3. AI#1 investigates -> `ai1_findings.md`
4. AI#2 review -> `ai2_review.md` (single one-shot `ollama run`; no session exists to continue)
5. AI#1 reads review, writes `decision.md` (first line: `DECISION: ACCEPT` or `DECISION: REJECT` + override_reason)
6. Test gate: if tests regress, AI#1 gets up to 3 self-fix rounds (critic is never re-consulted)
7. `final_report.md` with handoff summary; row appended to `audit_log.csv`

## Rules enforced by design
- One consultation per job: `consult_critic()` is the only call site for Ollama.
- AI#1 cannot talk to AI#2: prompts forbid it; prompts are short and file-referenced.
- Free-tier survival: STOP_BETWEEN_JOBS=1 halts after each job so you can swap
  ENGINE=claude <-> codex when one hits its rate cap. Handoff summaries in
  final_report.md let a fresh session continue.
- Resume-safe: jobs with an existing decision.md are skipped.

## Why findings are evidence-based
Small-sample regime: 6128 matches -> 340 training samples -> ~68/fold. Both AIs are
instructed to distrust conclusions without numbers. Runner tools (`tools/inspect_*.py`)
compute every cited quantity (duplicate dates, window call sites, flow flags) so the
critic grades real artifacts instead of prose.

## Critic model choice
qwen2.5-coder:7b is the recommended critic: code-aware, different model family from
Claude/GPT/Mistral (catches different errors), free and rate-limit-free locally.
phi4-mini works for triage but misses subtle ordering bugs in testing.

## Manual intervention points
- Read `jobs/<id>/ai2_review.md` before AI#1 decides (it runs unattended by default).
  Ctrl-C between steps is always safe; re-running resumes cleanly.
- `risk_level: medium` jobs (003, 004) touch the leakage/CV core: review decision.md
  before running the next job.
