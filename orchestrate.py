#!/usr/bin/env python3
"""Two-AI orchestrator for ML_Predictor2026_V2.

AI#1 (orchestrator): Claude Code (`claude -p`) or Codex (`codex exec`).
- May edit files and run Python/pytest inside the repo.
- Has final authority; may accept or reject the critic's recommendations.

AI#2 (critic): local Ollama model.
- Read-only and bounded: initial review plus at most one verification call.
- Invoked only via consult_critic().

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
MAX_TEST_FIX_ROUNDS = 3  # AI#1 self-corrections; AI#2 is not consulted here.

# Small-model budgets. Keep these conservative for qwen2.5-coder:7b.
FINDINGS_CHAR_BUDGET = int(os.environ.get("FINDINGS_CHAR_BUDGET", "8000"))
EVIDENCE_CHAR_BUDGET = int(os.environ.get("EVIDENCE_CHAR_BUDGET", "6000"))
VERIFICATION_CHAR_BUDGET = int(os.environ.get("VERIFICATION_CHAR_BUDGET", "6000"))
MAX_EVIDENCE_FILES = int(os.environ.get("MAX_EVIDENCE_FILES", "5"))
MAX_EVIDENCE_FILE_CHARS = int(os.environ.get("MAX_EVIDENCE_FILE_CHARS", "2500"))

CONSTRAINTS = """
HARD CONSTRAINTS (violations invalidate the job):
- You are AI#1, the orchestrator and final decision-maker for this job.
- You may edit project files and run Python / pytest.
- You may NOT invoke ollama, lmstudio, or any local model. Critic input arrives as a file only.
- One job = one investigation, at most two critic inputs (initial review and optional verification), one final decision.
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
    # SECURITY: shlex.split avoids shell=True, preventing sandbox escapes
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


# ---------------------------------------------------------------- helpers
def _read_text_safe(path: pathlib.Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"[unreadable file: {exc}]"

    if len(text) > limit:
        return text[:limit] + f"\n[truncated {len(text) - limit} chars]"
    return text


def read_job_text(path: pathlib.Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return fallback


def collect_evidence(ro: pathlib.Path) -> str:
    """Collect a small, bounded evidence packet from runner_output for AI#2."""
    if not ro.exists():
        return "(no runner_output directory)"

    files = [p for p in ro.rglob("*") if p.is_file()]
    if not files:
        return "(empty runner_output directory)"

    def priority(p: pathlib.Path):
        try:
            size = p.stat().st_size
        except OSError:
            size = 999_999_999
        return (p.name != "commands.log", size, p.name)

    files.sort(key=priority)
    files = files[:MAX_EVIDENCE_FILES]

    chunks = []
    used = 0

    for p in files:
        if used >= EVIDENCE_CHAR_BUDGET:
            break

        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            rel = p.name

        header = f"--- {rel} ---\n"
        max_body = min(
            MAX_EVIDENCE_FILE_CHARS,
            EVIDENCE_CHAR_BUDGET - used - len(header) - 20
        )

        if max_body <= 100:
            break

        body = _read_text_safe(p, max_body)
        chunk = header + body + "\n"
        chunks.append(chunk)
        used += len(chunk)

    return "\n".join(chunks) if chunks else "(no evidence included)"


def parse_enum(text: str, label: str, choices, default: str) -> str:
    """Parse labelled outputs robustly, e.g. JUDGMENT: PASS or **JUDGMENT:** PASS."""
    pattern = rf"{label}[^A-Za-z0-9_]*({'|'.join(choices)})"
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).upper() if m else default


def normalize_judgment(judgment: str, confidence: str) -> str:
    """Confidence-gated critic judgment.

    BLOCK requires HIGH confidence.
    REVISE requires MEDIUM or HIGH confidence.
    Otherwise downgrade to PASS.
    """
    if judgment == "BLOCK":
        if confidence == "HIGH":
            return "BLOCK"
        return "REVISE" if confidence == "MEDIUM" else "PASS"

    if judgment == "REVISE":
        return "PASS" if confidence == "LOW" else "REVISE"

    return "PASS"


def git_change_summary() -> str:
    try:
        r = subprocess.run(
            ["git", "--no-pager", "diff", "--stat"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
    except Exception:
        return "[git diff unavailable]"

    if r.returncode != 0:
        return "[git diff failed]"

    out = (r.stdout or "").strip()
    return out[:2000] if out else "[no unstaged changes]"


# ---------------------------------------------------------------- job flow
def do_job(job_id: str):
    jd = JOBS / job_id
    job = json.loads((jd / "job.json").read_text(encoding="utf-8"))

    # max_reviews:
    #   1 = strict one-shot critic review
    #   2 = initial review + optional verification call
    max_reviews = int(job.get("max_reviews", 2))
    assert 1 <= max_reviews <= 2, (
        "This harness allows at most two critic calls: initial review + optional verification."
    )

    ro = jd / "runner_output"
    ro.mkdir(parents=True, exist_ok=True)

    # Remove stale follow-up artifacts if a previous run stopped before decision.md.
    for stale in ("ai1_response.md", "ai2_verification.md"):
        try:
            (jd / stale).unlink()
        except FileNotFoundError:
            pass

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
        f"Keep it under {FINDINGS_CHAR_BUDGET} characters because a small critic model will read it.\n"
        f"Then reply with a 5-line completion summary only."
    )

    findings = read_job_text(
        jd / "ai1_findings.md",
        "ERROR: AI#1 did not write ai1_findings.md"
    )

    evidence = collect_evidence(ro)

    # 2. Initial consultation with AI#2
    critic_prompt = (
        f"You are AI#2, a read-only code/data auditor reviewing another AI's findings.\n"
        f"{CONSTRAINTS}\n"
        f"JOB GOAL: {job['goal']}\n"
        f"=== PRIMARY EVIDENCE ===\n{evidence}\n"
        f"=== AI#1 FINDINGS ===\n{findings[:FINDINGS_CHAR_BUDGET]}\n"
        f"BEHAVIORAL CONSTRAINTS:\n"
        f"- Use only the evidence and findings text above.\n"
        f"- Do not invent hypothetical risks or repeat pedantic disclaimers.\n"
        f"- Confidence means strength of evidence, not general caution.\n"
        f"Output exactly these labelled items:\n"
        f"JUDGMENT: PASS | REVISE | BLOCK\n"
        f"CONFIDENCE: HIGH | MEDIUM | LOW\n"
        f"FINDINGS REVIEW: table of each AI#1 finding rated valid / unsupported / needs_more_evidence, with confidence\n"
        f"TOP RISKS: max 3\n"
        f"REQUIRED MINIMAL FIXES: max 3, or NONE\n"
        f"JUDGMENT RULES:\n"
        f"- BLOCK only with HIGH confidence and concrete evidence of a hard constraint violation, leakage, or incorrect conclusion.\n"
        f"- REVISE with MEDIUM or HIGH confidence and concrete minimal fixes.\n"
        f"- If evidence is missing, unclear, or only hypothetical, use LOW confidence and PASS.\n"
    )

    review = consult_critic(critic_prompt)
    (jd / "ai2_review.md").write_text(review, encoding="utf-8")

    raw_judgment = parse_enum(review, "JUDGMENT", ["PASS", "REVISE", "BLOCK"], "PASS")
    confidence = parse_enum(review, "CONFIDENCE", ["HIGH", "MEDIUM", "LOW"], "LOW")
    judgment = normalize_judgment(raw_judgment, confidence)

    if raw_judgment != judgment:
        print(f"critic raw judgment {raw_judgment}/{confidence} normalized to {judgment}")

    response = ""
    verification = ""
    verification_status = ""
    verification_confidence = ""

    # 2b. Optional bounded verification pass.
    # This is still not a debate loop: at most one follow-up critic call.
    if judgment in {"REVISE", "BLOCK"} and max_reviews >= 2:
        call_ai1(
            f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
            f"Read jobs/{job_id}/ai1_findings.md and jobs/{job_id}/ai2_review.md.\n"
            f"Critic enforced judgment: {judgment}; confidence: {confidence}.\n"
            f"Apply only the minimal evidence-backed fixes needed to address the critic's concrete concerns.\n"
            f"These edits are provisional until decision.md is written.\n"
            f"If a recommendation is unsupported, reject it instead of changing code.\n"
            f"Write jobs/{job_id}/ai1_response.md with:\n"
            f"RESPONSE_ACTION: FIXED | PARTIAL | REJECTED\n"
            f"CHANGES: bullet list with file paths\n"
            f"REJECTED_RECOMMENDATIONS: bullet list or NONE\n"
            f"RATIONALE: evidence-based explanation\n"
            f"Include short changed-code/evidence snippets (max 40 lines total) so a read-only verifier can check.\n"
            f"Then reply with one line only."
        )

        response = read_job_text(
            jd / "ai1_response.md",
            "ERROR: AI#1 did not write ai1_response.md"
        )

        diff_stat = git_change_summary()

        verification_prompt = (
            f"You are AI#2, a read-only verifier. This is your only follow-up check.\n"
            f"{CONSTRAINTS}\n"
            f"JOB GOAL: {job['goal']}\n"
            f"=== ORIGINAL AI#2 REVIEW ===\n{review[:VERIFICATION_CHAR_BUDGET]}\n"
            f"=== AI#1 RESPONSE ===\n{response[:VERIFICATION_CHAR_BUDGET]}\n"
            f"=== GIT CHANGE SUMMARY ===\n{diff_stat}\n"
            f"Task: decide whether AI#1's response and change summary address the concrete concerns from your original review.\n"
            f"Do not introduce new hypothetical concerns unless the change summary clearly shows them.\n"
            f"Output exactly these labelled items:\n"
            f"VERIFICATION: CONFIRMED | STILL_CONCERNED\n"
            f"CONFIDENCE: HIGH | MEDIUM | LOW\n"
            f"REASON: one line\n"
            f"Rules:\n"
            f"- CONFIRMED only if the response gives concrete evidence the required minimal fixes were applied or validly refuted.\n"
            f"- If unclear, use STILL_CONCERNED.\n"
        )

        verification = consult_critic(verification_prompt)
        (jd / "ai2_verification.md").write_text(verification, encoding="utf-8")

        verification_status = parse_enum(
            verification,
            "VERIFICATION",
            ["CONFIRMED", "STILL_CONCERNED"],
            "STILL_CONCERNED"
        )
        verification_confidence = parse_enum(
            verification,
            "CONFIDENCE",
            ["HIGH", "MEDIUM", "LOW"],
            "LOW"
        )

    # 3. AI#1 decides once
    read_files = [
        f"jobs/{job_id}/ai1_findings.md",
        f"jobs/{job_id}/ai2_review.md"
    ]

    if (jd / "ai1_response.md").exists():
        read_files.append(f"jobs/{job_id}/ai1_response.md")

    if (jd / "ai2_verification.md").exists():
        read_files.append(f"jobs/{job_id}/ai2_verification.md")

    read_list = " and ".join(read_files)

    verification_note = ""
    if verification_status:
        verification_note = f" Verification: {verification_status} ({verification_confidence})."

    still_note = ""
    if verification_status == "STILL_CONCERNED":
        still_note = (
            "If the critic is STILL_CONCERNED, either address the remaining concern with evidence "
            "or choose REJECT.\n"
        )

    (jd / "final_report.md").touch(exist_ok=True)

    call_ai1(
        f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
        f"Read {read_list}.\n"
        f"Critic enforced judgment: {judgment}; confidence: {confidence}.{verification_note}\n"
        f"Write jobs/{job_id}/decision.md containing on the first line exactly "
        f"'DECISION: ACCEPT' or 'DECISION: REJECT', then: which recommendations were applied or rejected, "
        f"and if REJECT an override_reason (what evidence makes the recommendation unnecessary, "
        f"and what future evidence would change your mind).\n"
        f"If ACCEPT: apply any remaining evidence-backed changes now with edits/pytest, and record every edit in final_report.md.\n"
        f"If REJECT: revert any provisional edits made for the critic response unless they are independently required and justified in decision.md.\n"
        f"{still_note}"
        f"Then reply with the decision line only."
    )

    decision = read_job_text(jd / "decision.md", "")

    # Robust line parsing to handle markdown bolding/format shifts.
    dec = parse_enum(decision, "DECISION", ["ACCEPT", "REJECT"], "REJECT")

    override = "yes" if dec == "REJECT" else "no"

    # Also flag overrides when AI#1 proceeds despite an unresolved critic concern.
    if dec == "ACCEPT" and verification_status == "STILL_CONCERNED":
        override = "yes"

    if dec == "ACCEPT" and judgment == "BLOCK" and verification_status != "CONFIRMED":
        override = "yes"

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
            f"Reply with one line: FIXED or REVERTED."
        )
    else:
        with (jd / "final_report.md").open("a", encoding="utf-8") as f_rep:
            f_rep.write(
                f"\nWARNING: tests still failing after {MAX_TEST_FIX_ROUNDS} self-fix rounds. "
                f"Human review required. Reverting workspace to clean state.\n"
            )
        # Automated git checkout self-healing gate.
        subprocess.run(["git", "checkout", "--", "."], cwd=ROOT, capture_output=True, text=True)

    # 5. Close out
    critic_summary = f"critic judgment {judgment}/{confidence}"
    if verification_status:
        critic_summary += f", verification {verification_status}/{verification_confidence}"

    call_ai1(
        f"You are AI#1 orchestrator. {CONSTRAINTS}\n"
        f"Finalize jobs/{job_id}/final_report.md: goal, evidence, findings, review summary, "
        f"{critic_summary}, decision ({dec}), changes made, test results before/after, and one-paragraph handoff "
        f"summary for a fresh AI session (this is what future jobs will read as context).\n"
        f"Reply with one line: DONE."
    )

    _, ta_tail = run_tests()

    log({
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "job_id": job_id,
        "engine": ENGINE,
        "critic_model": CRITIC_MODEL,
        "decision": dec,
        "override": override,
        "tests_before": tb_tail,
        "tests_after": ta_tail
    })

    print(f"=== {job_id} closed: {dec} | {critic_summary} | tests: {tb_tail} -> {ta_tail} ===")


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