#!/usr/bin/env python
"""
ML_Predictor2026_V2 - Preflight Environment & Data Staleness Checker
Executed at SessionStart by Antigravity lifecycle hook.
"""

import sys
import os
import json
import datetime
from pathlib import Path

def main():
    try:
        # Read hook payload from stdin if available
        stdin_data = sys.stdin.read().strip()
        workspace_dir = Path.cwd()
        if stdin_data:
            try:
                payload = json.loads(stdin_data)
                paths = payload.get("workspacePaths", [])
                if paths:
                    workspace_dir = Path(paths[0])
            except Exception:
                pass

        alerts = []
        info = []

        # 1. Check data/ARG.csv
        arg_path = workspace_dir / "data" / "ARG.csv"
        if not arg_path.exists():
            alerts.append("[ALERT] data/ARG.csv missing! Run data ingestion before predicting.")
        else:
            mtime = datetime.datetime.fromtimestamp(arg_path.stat().st_mtime)
            age_days = (datetime.datetime.now() - mtime).days
            with open(arg_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = sum(1 for _ in f) - 1
            if age_days >= 5:
                alerts.append(f"[WARNING] data/ARG.csv is {age_days} days old ({lines} matches). Consider updating from football-data.co.uk.")
            else:
                info.append(f"[OK] data/ARG.csv is fresh ({age_days}d old, {lines} matches).")

        # 2. Check Partidos.txt
        partidos_path = workspace_dir / "Partidos.txt"
        if not partidos_path.exists():
            partidos_path = workspace_dir / "partidos.txt"
        
        if not partidos_path.exists():
            alerts.append("[ALERT] Partidos.txt not found. Weekly fixtures need to be provided.")
        else:
            with open(partidos_path, "r", encoding="utf-8", errors="ignore") as f:
                fixtures = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            info.append(f"[OK] Partidos.txt contains {len(fixtures)} fixture(s) ready for inference.")

        # 3. Check Glossary.txt
        glossary_path = workspace_dir / "Glossary.txt"
        if not glossary_path.exists():
            alerts.append("[WARNING] Glossary.txt missing from project root.")
        else:
            info.append("[OK] Glossary.txt present.")

        # 4. Check .venv
        venv_python = workspace_dir / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            alerts.append("[WARNING] Virtual environment (.venv) not found at expected path.")
        else:
            info.append("[OK] Python virtual environment ready.")

        # Build message
        report_lines = [
            "============================================================",
            " ML_Predictor2026_V2 - Environment Preflight Check",
            "============================================================"
        ]
        report_lines.extend(info)
        if alerts:
            report_lines.append("------------------------------------------------------------")
            report_lines.extend(alerts)
        report_lines.append("============================================================")

        report_text = "\n".join(report_lines)

        output = {
            "injectSteps": [
                {
                    "systemMessage": {
                        "systemMessage": report_text
                    }
                }
            ]
        }
        print(json.dumps(output))
    except Exception:
        # Graceful fallback: return empty JSON so hook never blocks
        print(json.dumps({}))

if __name__ == "__main__":
    main()
