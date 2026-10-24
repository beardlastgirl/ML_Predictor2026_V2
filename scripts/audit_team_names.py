#!/usr/bin/env python
"""
ML_Predictor2026_V2 - Team Glossary Auditor
Audits team names in fixture files or scraped data against Glossary.txt.
Identifies unmapped teams, suggests closest matches, and formats new glossary lines.
"""

import sys
import os
import difflib
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_processing import load_glossary, normalize_team_name
from src.normalization import canonicalize_name


def audit_names(names_to_check, glossary_path="Glossary.txt"):
    glossary = load_glossary(glossary_path)
    
    # Extract known canonical targets (the normalized names in ARG.csv)
    # Read raw Glossary.txt to find unique target names
    canonical_targets = set()
    if os.path.exists(glossary_path):
        with open(glossary_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    for sep in ["->", "=", ":"]:
                        if sep in line:
                            target = line.split(sep, 1)[1].strip()
                            canonical_targets.add(target)
                            break

    unmapped = []
    mapped = []

    for name in names_to_check:
        clean_name = name.strip()
        if not clean_name or clean_name.startswith("#"):
            continue
            
        norm = normalize_team_name(clean_name, glossary)
        # If normalization returns the exact same string canonicalized, check if it's a known target
        canonical_clean = canonicalize_name(clean_name)
        is_known = norm in canonical_targets or canonical_clean in [canonicalize_name(t) for t in canonical_targets]
        
        if is_known or norm in glossary.values():
            mapped.append((clean_name, norm))
        else:
            # Find closest canonical suggestions
            suggestions = difflib.get_close_matches(clean_name, list(canonical_targets), n=3, cutoff=0.4)
            unmapped.append((clean_name, suggestions))

    print("=" * 60)
    print(" Team Name Glossary Audit Report")
    print("=" * 60)
    print(f"Total checked: {len(names_to_check)}")
    print(f"Mapped successfully: {len(mapped)}")
    print(f"Unmapped / Ambiguous: {len(unmapped)}")
    print("-" * 60)

    if unmapped:
        print("\n[ATTENTION] Unmapped team names detected:")
        for raw, sugg in unmapped:
            print(f"  • Raw Name: '{raw}'")
            if sugg:
                print(f"    Suggested Target: {sugg[0]} (Alternatives: {', '.join(sugg[1:])})")
                print(f"    Proposed Glossary Entry: {raw} -> {sugg[0]}")
            else:
                print("    No close match found. Check ARG.csv for the official team name.")
            print()
    else:
        print("\n[OK] All team names successfully resolve to canonical names!")

    print("=" * 60)
    return len(unmapped) == 0


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "Partidos.txt"
    if not os.path.exists(target_file):
        print(f"[ERROR] Target file not found: {target_file}")
        sys.exit(1)

    teams = []
    with open(target_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "-" in line:
                parts = line.split("-", 1)
                teams.append(parts[0].strip())
                teams.append(parts[1].strip())
            else:
                teams.append(line)

    success = audit_names(teams)
    sys.exit(0 if success else 1)
