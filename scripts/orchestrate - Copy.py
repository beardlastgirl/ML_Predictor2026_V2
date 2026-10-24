#!/usr/bin/env python3
"""Two-AI orchestrator for ML_Predictor2026_V2.
AI#1 (orchestrator): Claude Code (`claude -p`) or Codex (`codex exec`).
- May edit files and run Python/pytest inside the repo.
- Has final authority; may accept or reject the critic's recommendations.
AI#2 (critic): local Ollama model, consulted EXACTLY ONCE per job.
- Read-only, one-shot, invoked only via the single call site below.
Usage:
set ENGINE=claude                 # or codex
set CRITIC_MODEL=qwen2.5-coder:7b
python orchestrate.py             # processes jobs/queue.json in order
Resume-safe: a job with an existing decision.md is skipped.
"""
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
AUDIT = ROOT / "audit_log.csv"
ENGINE = os.environ.get("ENGINE", "claude").lower()
CRITIC_MODEL = os.environ.get("CRITIC_MODEL", "qwen2.5-coder:7b")
MAX_TEST_FIX_ROUNDS = 3  # AI#1 self-corrections; AI#2 is never re-consulted
CONSTRAINTS = """
HARD CONSTRAINTS (violations invalidate the job):
- You are AI#1, the orchestrator and final decision-maker for this job.
- You may edit project files and run Python / pytest.
- You may NOT invoke ollama, lmstudio, or any local model. Critic input arrives as a file only.
- One job = one investigation, one critic review (provided to you), one final decision.
- Do not conclude that data leakage exists solely because multiple matches share a date.
Leakage requires evidence that information from match t (or later) influenced features or labels for match t.
- Small-sample regime (~340 training samples, ~68/fold): do not claim statistical significance without numbers.
- Every claim must cite evidence: file path + line, runner_output artifact, or computed number.
"""

# ---------------------------------------------------------------- engines
def call_ai1(prompt: str) -> str:
    """Short prompts only: AI#1 reads full artifacts from disk via its own file tools."""
    if ENGINE == "claude":
        args = ["claude", "-p", prompt,
                "--output-format", "text",
                "--permission-mode", "acceptEdits"]
    elif ENGINE == "codex":
        args = ["codex", "exec",
                "--sandbox", "workspace-write",
                "--ask-for-approval", "never",
                "--cd", str(ROOT), prompt]
    else:
        raise SystemExit(f"Unknown ENGINE={ENGINE!r} (use claude|codex)")
    
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=3600)
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        out += f"\n[exit {r.returncode} | stderr]\n" + (r.stderr or "")[-2000:]
    return out

def consult_critic(prompt: str) -> str:
    """THE ONLY path to AI#2. One subprocess, no session, no history, no reply."""
    r = subprocess.run(["ollama", "run", CRITIC_MODEL], input=prompt,
                       capture_output=True, text=True, timeout=1200)
    return (r.stdout or "").strip() + ("\n[stderr]\n" + r.stderr[-1000:] if r.returncode else "")

def run_cmd(cmd: str) -> str:
    # [1] SECURITY: shlex.split avoids shell=True, preventing sandbox escapes 
    # if job.json contains malicious shell injections.
    try:
        args = shlex.split(cmd)
    except ValueError as e:
        return f"$ {cmd}\n[error parsing command: {e}]"
        
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    return f"$ {cmd}\n[exit {r.returncode}]\n{r.stdout}\n{r.stderr}"[-4000:]

def run_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
                       cwd=ROOT, capture_output=True, text=True, timeout=1800)
    tail = (r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else ""
    return r.returncode, tail

def log(row: dict):
    new = not AUDIT.exists()
    with AUDIT.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "job_id", "engine", "critic_model", 
            "decision", "override", "tests_before", "tests_after"
        ])
        if new:
            writer.writeheader()
        writer.writerow(row)

# ---------------------------------------------------------------- job flow
def do_job(job_id: str):
    jd = JOBS / job_id
    job = json.loads((jd / "job.json").read_text(encoding="utf-8"))
    assert job.get("max_reviews", 1) == 1, "This harness implements exactly one consultation per job."
    
    ro = jd / "runner_output"
    ro.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {job_id} | engine={ENGINE} | critic={CRITIC_MODEL} ===")
    
    # 0. Deterministic evidence + baseline tests
    with (ro / "commands.log").open("a", encoding="utf-8") as f_log:
        for c in job["commands"]:
            f_log.write(run_cmd(c) + "\n")
            
    tb_code, tb_tail = run_tests()
    (jd / "tests_before.txt").write_text(tb_tail, encoding="utf-8")
    
    # 1. AI#1 investigates and writes findings
    call_ai1(
        f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
        f"Job file: jobs/{job_id}/job.json\n"
        f"Evidence: jobs/{job_id}/runner_output/ (read every file; do not re-derive by guess)\n"
        f"Task: {job['goal']}\n"
        f"Write jobs/{job_id}/ai1_findings.md with: Summary / Evidence (cited) / "
        f"Findings with severity+confidence / What would confirm or falsify each / Proposed action.\n"
        f"Then reply with a 5-line completion summary only.")
    findings = (jd / "ai1_findings.md").read_text(encoding="utf-8")
    
    # 2. THE one consultation with AI#2
    critic_prompt = (
        f"You are AI#2, a read-only code/data auditor reviewing another AI's findings.\n"
        f"{CONSTRAINTS}\n"
        f"JOB GOAL: {job['goal']}\n"
        f"=== AI#1 FINDINGS ===\n{findings[:18000]}\n"
        # [2] BEHAVIORAL FIX: Qwen repetition & hallucination blockers
        f"BEHAVIORAL CONSTRAINTS:\n"
        f"- Default to PASS if you cannot back a concern with plain evidence from the text.\n"
        f"- Do not invent hypothetical risks or repeat pedantic disclaimers.\n"
        f"Output exactly:\n"
        f"1. JUDGMENT: PASS | REVISE | BLOCK\n"
        f"2. FINDINGS REVIEW: table of each AI#1 finding rated valid / unsupported / needs_more_evidence\n"
        f"3. TOP RISKS: max 3\n"
        f"4. REQUIRED MINIMAL FIXES: max 3, or NONE")
    review = consult_critic(critic_prompt)
    (jd / "ai2_review.md").write_text(review, encoding="utf-8")
    
    # 3. AI#1 decides once
    (jd / "final_report.md").touch(exist_ok=True) 
    call_ai1(
        f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
        f"Read jobs/{job_id}/ai1_findings.md and jobs/{job_id}/ai2_review.md.\n"
        f"Write jobs/{job_id}/decision.md containing on the first line exactly "
        f"'DECISION: ACCEPT' or 'DECISION: REJECT', then: which recommendations were applied or rejected, "
        f"and if REJECT an override_reason (what evidence makes the recommendation unnecessary, "
        f"and what future evidence would change your mind).\n"
        f"If ACCEPT: apply the changes now with edits/pytest, and record every edit in final_report.md.\n"
        f"Then reply with the decision line only.")
    
    decision = (jd / "decision.md").read_text(encoding="utf-8")
    
    # [4] ROBUSTNESS FIX: Fuzzy line parsing to handle markdown bolding/format shifts
    if re.search(r"DECISION:\s*ACCEPT", decision, re.IGNORECASE):
        dec = "ACCEPT"
    elif re.search(r"DECISION:\s*REJECT", decision, re.IGNORECASE):
        dec = "REJECT"
    else:
        dec = "REJECT" # Safe default
        
    override = "yes" if dec == "REJECT" else "no"
    
    # 4. Test gate (independent of AI#1's opinion)
    for i in range(MAX_TEST_FIX_ROUNDS):
        ta_code, ta_tail = run_tests()
        if ta_code == 0:
            break
        call_ai1(
            f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
            f"Job {job_id}: tests regressed after your changes.\n"
            f"Last pytest line: {ta_tail}\n"
            f"Either fix the changes or revert them (prefer the minimal correct fix). "
            f"Update jobs/{job_id}/final_report.md with what you did. Do not consult anyone. "
            f"Reply with one line: FIXED or REVERTED.")
    else:
        with (jd / "final_report.md").open("a", encoding="utf-8") as f_rep:
            f_rep.write(
                f"\nWARNING: tests still failing after {MAX_TEST_FIX_ROUNDS} self-fix rounds. "
                f"Human review required. Reverting workspace to clean state.\n"
            )
        # [3] STABILITY FIX: Automated git checkout self-healing gate
        subprocess.run(["git", "checkout", "--", "."], cwd=ROOT, capture_output=True, text=True)
    
    # 5. Close out
    call_ai1(
        f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
        f"Finalize jobs/{job_id}/final_report.md: goal, evidence, findings, review summary, "
        f"decision ({dec}), changes made, test results before/after, and one-paragraph handoff "
        f"summary for a fresh AI session (this is what future jobs will read as context). "
        f"Reply with one line: DONE.")
    _, ta_tail = run_tests()
    
    log({"timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
         "job_id": job_id, "engine": ENGINE, "critic_model": CRITIC_MODEL,
         "decision": dec, "override": override,
         "tests_before": tb_tail, "tests_after": ta_tail})
    print(f"=== {job_id} closed: {dec} | tests: {tb_tail} -> {ta_tail} ===")

def main():
    queue = json.loads((JOBS / "queue.json").read_text(encoding="utf-8"))
    for job_id in queue:
        if (JOBS / job_id / "decision.md").exists():
            print(f"skip {job_id} (decision.md exists)")
            continue
        do_job(job_id)
        
        if os.environ.get("STOP_BETWEEN_JOBS", "1") == "1":
            print("STOP_BETWEEN_JOBS=1 -> halting. Re-run to continue the queue.")
            break

if __name__ == "__main__":
    main()