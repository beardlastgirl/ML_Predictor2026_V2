#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_team_names.py - Audit script for team name mappings.

Compares Glossary.txt mappings against data/ARG.csv to identify
mismatches, dead mappings, and potential silent failures.
"""

import os
import sys
import pandas as pd
from src.data_processing import load_glossary, normalize_team_name
from src.utils import log_info, log_ok, log_error, log_warning

def run_audit(glossary_path="Glossary.txt", data_path="data/ARG.csv", report_path="DEV_CONTEXT/TEAM_NAME_AUDIT.md"):
    log_info(f"Starting team name audit...")
    
    # 1. Load Glossary
    glossary = load_glossary(glossary_path)
    if not glossary:
        log_error("Could not load glossary. Exiting.")
        return

    # 2. Load data/ARG.csv
    if not os.path.exists(data_path):
        log_error(f"Data file not found: {data_path}")
        return
    
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        log_error(f"Error reading CSV: {e}")
        return

    if 'Home' not in df.columns or 'Away' not in df.columns:
        log_error("CSV must contain 'Home' and 'Away' columns.")
        return

    # 3. Extract unique teams from ARG.csv
    raw_teams = set(df['Home'].dropna().unique()) | set(df['Away'].dropna().unique())
    
    # 4. Canonical glossary values
    canonical_values = set(glossary.values())
    
    # 5. Analyze teams
    mismatches = []
    used_canonical = set()
    
    normalized_to_raw = {}
    
    for raw_name in raw_teams:
        # Check if the raw name exists in glossary BEFORE normalization
        # Note: load_glossary stores keys in UPPER case
        raw_upper = str(raw_name).strip().upper()
        
        normalized = normalize_team_name(raw_name, glossary)
        used_canonical.add(normalized)
        
        if normalized not in normalized_to_raw:
            normalized_to_raw[normalized] = []
        normalized_to_raw[normalized].append(raw_name)
        
        # If not in glossary and normalization changed it, it might be a mismatch
        # or if it's in glossary, we track it
        if raw_upper not in glossary:
            # If normalized name is different from basic upper-case-stripped name
            basic_normalized = str(raw_name).strip().upper()
            if normalized != basic_normalized:
                mismatches.append((raw_name, normalized))
    
    # 6. Dead mappings (canonical values never used)
    dead_mappings = sorted(list(canonical_values - used_canonical))
    
    # 7. Potential duplicates (different normalized names that look similar)
    # This is heuristic-based
    
    # 8. Report generation
    report_lines = []
    report_lines.append("# Team Name Mapping Audit")
    report_lines.append(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    report_lines.append(f"- **Total unique teams in ARG.csv:** {len(raw_teams)}")
    report_lines.append(f"- **Total glossary mappings:** {len(glossary)}")
    report_lines.append(f"- **Total canonical teams used:** {len(used_canonical)}")
    report_lines.append("")
    
    report_lines.append("## Teams in ARG.csv with no glossary match")
    report_lines.append("These teams were normalized using default rules because no direct mapping was found in Glossary.txt.")
    report_lines.append("")
    
    no_match_teams = []
    for raw_name in sorted(list(raw_teams)):
        raw_upper = str(raw_name).strip().upper()
        if raw_upper not in glossary:
            norm = normalize_team_name(raw_name, glossary)
            no_match_teams.append(f"- {raw_name} -> {norm}")
    
    if no_match_teams:
        report_lines.extend(no_match_teams)
    else:
        report_lines.append("None found.")
    report_lines.append("")
    
    report_lines.append("## Glossary entries that never appear in ARG.csv")
    report_lines.append("These canonical names exist in the glossary but were not found in the Home/Away columns of ARG.csv.")
    report_lines.append("")
    if dead_mappings:
        for dead in dead_mappings:
            report_lines.append(f"- {dead}")
    else:
        report_lines.append("None found.")
    report_lines.append("")
    
    # Heuristic for potential duplicates
    report_lines.append("## Potential Duplicates/Inconsistencies")
    report_lines.append("Heuristic check for teams that might be the same but have different canonical names.")
    report_lines.append("")
    
    sorted_canonical = sorted(list(used_canonical))
    potential_dupes = []
    for i in range(len(sorted_canonical)):
        for j in range(i + 1, len(sorted_canonical)):
            t1 = sorted_canonical[i]
            t2 = sorted_canonical[j]
            # Simple similarity: if one is a substring of the other or very similar
            if (t1 in t2 or t2 in t1) and len(t1) > 4:
                potential_dupes.append(f"- {t1} vs {t2}")
    
    if potential_dupes:
        report_lines.extend(potential_dupes)
    else:
        report_lines.append("No obvious duplicates found.")
    
    report_content = "\n".join(report_lines)
    
    # Print report
    print("\n" + "="*40)
    print("AUDIT REPORT SUMMARY")
    print("="*40)
    print(f"Total unique teams in ARG.csv: {len(raw_teams)}")
    print(f"Total glossary mappings: {len(glossary)}")
    print(f"Teams without glossary match: {len(no_match_teams)}")
    print(f"Dead glossary entries: {len(dead_mappings)}")
    print("="*40 + "\n")
    
    # Write to file
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    log_ok(f"Full audit report written to {report_path}")

if __name__ == "__main__":
    run_audit()
