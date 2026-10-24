#!/usr/bin/env python
"""
ML_Predictor2026_V2 - Fast Test Guard Hook (PostToolUse)
Automatically verifies math and temporal invariants when core source code changes.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

def main():
    try:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            print(json.dumps({}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        target_file = args.get("TargetFile", "")
        # Normalize path
        normalized_target = target_file.replace("\\", "/").lower()

        # Only trigger when source files in src/ are edited
        if "/src/" in normalized_target and normalized_target.endswith(".py"):
            workspace_dir = Path.cwd()
            venv_python = workspace_dir / ".venv" / "Scripts" / "python.exe"
            python_cmd = str(venv_python) if venv_python.exists() else "python"

            test_cmd = [
                python_cmd,
                "-m", "pytest",
                "tests/test_golden_math.py",
                "tests/test_temporal_ordering.py",
                "tests/test_leakage.py",
                "-q"
            ]

            proc = subprocess.run(
                test_cmd,
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=25
            )

            # Ensure logs directory exists
            log_dir = workspace_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / "fast_test_guard.log"

            with open(log_file, "a", encoding="utf-8") as f:
                if proc.returncode == 0:
                    f.write(f"[PASS] Fast tests passed after edit to {target_file}\n")
                else:
                    f.write(f"[FAIL] Fast tests FAILED after edit to {target_file}:\n{proc.stdout}\n{proc.stderr}\n")

    except Exception:
        pass
    finally:
        # PostToolUse contract expects empty JSON object
        print(json.dumps({}))

if __name__ == "__main__":
    main()
