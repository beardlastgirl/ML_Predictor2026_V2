#!/usr/bin/env python
"""
Standalone prediction CLI that outputs JSON (like FootballBin API)
"""

import argparse
import json
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.data_processing import load_glossary, normalize_team_name


def load_predictions():
    """Load latest predictions from results file"""
    import glob
    import re

    files = glob.glob(os.path.join(PROJECT_DIR, "Resultados_*.txt"))
    if not files:
        return {}

    # Sort by modification time (newest first)
    latest = max(files, key=os.path.getmtime)
    predictions = {}

    try:
        with open(latest, "r", encoding="utf-8") as f:
            current_match = None
            for line in f:
                line = line.strip()
                if " - " in line and "=" not in line and "---" not in line and "Resultado" not in line and "xG:" not in line and "Confianza" not in line and not line.startswith("Partidos"):
                    parts = line.split(" - ")
                    if len(parts) == 2:
                        # Store with normalized lowercase keys for matching
                        home_raw = parts[0].strip()
                        away_raw = parts[1].strip()
                        home_norm = home_raw.lower()
                        away_norm = away_raw.lower()
                        current_match = (home_norm, away_norm, home_raw, away_raw)
                        predictions[current_match] = {}
                elif "Resultado:" in line and current_match:
                    if "(" in line and ")" in line:
                        outcome = line[line.index("(")+1:line.index(")")]
                        score = line.replace("Resultado:", "").strip().split(" ")[0]
                        predictions[current_match]["score"] = score
                        predictions[current_match]["outcome"] = outcome
                elif "xG:" in line and current_match:
                    xg = line.replace("xG:", "").strip()
                    predictions[current_match]["xg"] = xg
                elif "Confianza:" in line and current_match:
                    conf = line.replace("Confianza:", "").strip()
                    predictions[current_match]["confidence"] = conf
    except Exception as e:
        print(f"Error loading predictions: {e}", file=sys.stderr)

    return predictions


def load_fixtures():
    """Load current fixtures"""
    glossary = load_glossary(os.path.join(PROJECT_DIR, "Glossary.txt"))

    fixtures_file = os.path.join(PROJECT_DIR, "partidos.txt")
    if not os.path.exists(fixtures_file):
        return []

    fixtures = []
    try:
        with open(fixtures_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip header lines and non-match lines
                if not line or "FECHA" in line or "penales" in line.lower() or "expulsados" in line.lower() or "goles" in line.lower():
                    continue
                if " - " in line:
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        home = normalize_team_name(parts[0].strip(), glossary)
                        away = normalize_team_name(parts[1].strip().rstrip(":"), glossary)
                        fixtures.append({
                            "home": home,
                            "away": away,
                            "date": "TBD"
                        })
    except Exception:
        pass

    return fixtures


def find_prediction(home, away, predictions):
    """Find prediction for a specific match"""
    home_lower = home.lower()
    away_lower = away.lower()

    for (h_norm, a_norm, h_raw, a_raw), pred in predictions.items():
        # Check various matching strategies
        if (home_lower in h_norm or h_norm in home_lower) and (away_lower in a_norm or a_norm in away_lower):
            return pred
        # Also try matching against raw names
        if home_lower in h_raw.lower() or h_raw.lower() in home_lower:
            if away_lower in a_raw.lower() or a_raw.lower() in away_lower:
                return pred
    return {}


def main():
    parser = argparse.ArgumentParser(description="Get Liga Argentina predictions")
    parser.add_argument("--home", help="Filter by home team")
    parser.add_argument("--away", help="Filter by away team")
    parser.add_argument("--matchweek", help="Matchweek number")
    args = parser.parse_args()

    fixtures = load_fixtures()
    predictions = load_predictions()

    # Apply filters
    if args.home:
        fixtures = [f for f in fixtures if args.home.lower() in f["home"].lower()]
    if args.away:
        fixtures = [f for f in fixtures if args.away.lower() in f["away"].lower()]

    matches = []
    for f in fixtures:
        pred = find_prediction(f["home"], f["away"], predictions)

        match = {
            "home_team": f["home"],
            "away_team": f["away"],
            "kickoff": f.get("date", "TBD"),
            "predictions": [
                {"type": "score", "value": pred.get("score", "TBD")},
                {"type": "outcome", "value": pred.get("outcome", "TBD")},
                {"type": "xg", "value": pred.get("xg", "TBD")},
                {"type": "confidence", "value": pred.get("confidence", "TBD")}
            ]
        }
        matches.append(match)

    response = {
        "league": "Liga Profesional Argentina",
        "matchweek": args.matchweek or "current",
        "count": len(matches),
        "matches": matches
    }

    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
