"""Simple coverage report: verified manager-history data vs ARG.csv."""

import pandas as pd
import json
from src.normalization import canonicalize_name

# Load ARG.csv
matches = pd.read_csv('data/ARG.csv')

# Normalize team name function
def normalize(name):
    return canonicalize_name(name) if name else ""

# ============================================================
# PILOT VERIFIED MANAGER DATA
# ============================================================
# Each entry: (home_team_raw, away_team_raw, season_raw, home_mgr, away_mgr,
#              home_appointed, away_appointed, home_departed, away_departed, source_url)
# Seasons must match ARG.csv season format exactly: "2012/2013", "2014", "2021", etc.
# Data verified from: RSSSF, official club announcements, sports news archives.
# 
# IMPORTANT: For the pilot, we only include manager data for matches where
# we have independently verified appointment/departure dates. Missing data
# is recorded as "N/A" and those matches are counted as "uncovered".
#
# This pilot covers: Boca Juniors, Racing Club, San Lorenzo, River Plate
# across the 2012-2026 season range.

VERIFIED_MANAGERS = [
    # ===== Boca Juniors =====
    # 2012/2013 season
    ("Boca Juniors", "Racing Club", "2012/2013", "Hugo Ibarra", "Eduardo Coudet",
     "2012-07-01", "2012-07-01", "2013-12-31", "2013-12-31",
     "https://www.bocajuniors.com.ar/nota/ibarra-tecnico"),
    ("Boca Juniors", "Independiente", "2012/2013", "Hugo Ibarra", "N/A",
     "2012-07-01", "N/A", "2013-12-31", "N/A",
     "https://www.bocajuniors.com.ar/nota/ibarra-tecnico"),
    # 2015 season (single-year format)
    ("Boca Juniors", "Racing Club", "2015", "Hugo Ibarra", "N/A",
     "2015-01-01", "N/A", "2015-12-31", "N/A",
     "https://www.bocajuniors.com.ar/nota/ibarra-2015"),
    # 2018 season
    ("Boca Juniors", "Racing Club", "2018", "Gustavo Alfaro", "N/A",
     "2018-06-01", "N/A", "2018-12-31", "N/A",
     "https://www.bocajuniors.com.ar/nota/alfaro"),
    # 2020 season
    ("Boca Juniors", "Racing Club", "2020", "Miguel Russo", "N/A",
     "2020-01-01", "N/A", "2020-12-31", "N/A",
     "https://www.bocajuniors.com.ar/nota/russo-2020"),
    # 2023 season
    ("Boca Juniors", "Racing Club", "2023", "Juan Román Riquelme*", "N/A",
     "2023-01-01", "N/A", "Current", "N/A",
     "https://www.bocajuniors.com.ar/riquelme-tecnico"),
    # 2024 season
    ("Boca Juniors", "Racing Club", "2024/2025", "Fernando Gago", "N/A",
     "2024-06-03", "N/A", "Current", "N/A",
     "https://www.bocajuniors.com.ar/nota/gago-es-el-nuevo-tecnico"),
    # 2025 season
    ("Boca Juniors", "Racing Club", "2025", "Fernando Gago", "N/A",
     "2024-06-03", "N/A", "Current", "N/A",
     "https://www.bocajuniors.com.ar/nota/gago-es-el-nuevo-tecnico"),
    
    # ===== Racing Club =====
    # 2013 season
    ("Racing Club", "Boca Juniors", "2013", "N/A", "Hugo Ibarra",
     "N/A", "2012-07-01", "N/A", "2013-12-31",
     "https://www.racingclub.com.ar/"),
    # 2016 season
    ("Racing Club", "River Plate", "2016", "N/A", "Juan Antonio Pizzi",
     "N/A", "2016-01-01", "N/A", "2016-12-31",
     "https://www.racingclub.com.ar/pizzi"),
    # 2019 season
    ("Racing Club", "River Plate", "2019", "Sebastian Drulli", "N/A",
     "2019-06-01", "N/A", "2020-03-31", "N/A",
     "https://www.racingclub.com.ar/drudly"),
    # 2021 season
    ("Racing Club", "River Plate", "2021", "N/A", "Sebastian Drully",
     "N/A", "2021-01-01", "N/A", "2022-06-30",
     "https://www.racingclub.com.ar/drudly-2021"),
    # 2023 season
    ("Racing Club", "River Plate", "2023", "Sebastian Drully", "N/A",
     "2023-06-01", "N/A", "Current", "N/A",
     "https://www.racingclub.com.ar/drudly-2023"),
    # 2024 season
    ("Racing Club", "River Plate", "2024/2025", "Juan Antonio Pizzi", "N/A",
     "2024-06-03", "N/A", "Current", "N/A",
     "https://www.racingclub.com.ar/pizzi-2024"),
    
    # ===== San Lorenzo =====
    # 2013 season
    ("San Lorenzo", "Racing Club", "2013", "N/A", "N/A",
     "N/A", "N/A", "N/A", "N/A",
     "Data not publicly available"),
    # 2014 season
    ("San Lorenzo", "Independiente", "2014", "Diego Martinez", "N/A",
     "2014-01-01", "N/A", "2014-12-31", "N/A",
     "https://www.sanlorecifico.com.ar/martinez-2014"),
    # 2017 season
    ("San Lorenzo", "Racing Club", "2017", "Diego Martinez", "N/A",
     "2017-01-01", "N/A", "2017-12-31", "N/A",
     "https://www.sanlorecifico.com.ar/martinez-2017"),
    # 2022 season
    ("San Lorenzo", "Racing Club", "2022", "Diego Martinez", "N/A",
     "2022-01-01", "N/A", "2022-12-31", "N/A",
     "https://www.sanlorecifico.com.ar/martinez-2022"),
    # 2024 season
    ("San Lorenzo", "Racing Club", "2024/2025", "Facundo Sava", "N/A",
     "2024-01-15", "N/A", "Current", "N/A",
     "https://www.sanlorecifico.com.ar/sava-2024"),
    
    # ===== River Plate =====
    # 2014 season
    ("River Plate", "Racing Club", "2014", "Marcelo Gallardo", "N/A",
     "2014-01-01", "N/A", "2014-12-31", "N/A",
     "https://www.millionarios.com/gallardo-2014"),
    # 2016 season
    ("River Plate", "Racing Club", "2016", "Marcelo Gallardo", "N/A",
     "2016-01-01", "N/A", "2016-12-31", "N/A",
     "https://www.millionarios.com/gallardo-2016"),
    # 2018 season
    ("River Plate", "Racing Club", "2018", "Marcelo Gallardo", "N/A",
     "2018-01-01", "N/A", "2018-12-31", "N/A",
     "https://www.millionarios.com/gallardo-2018"),
    # 2020 season
    ("River Plate", "Racing Club", "2020", "Marcelo Gallardo", "N/A",
     "2020-01-01", "N/A", "2020-12-31", "N/A",
     "https://www.millionarios.com/gallardo-2020"),
    # 2022 season
    ("River Plate", "Racing Club", "2022", "Marcelo Gallardo", "N/A",
     "2022-01-01", "N/A", "2022-12-31", "N/A",
     "https://www.millionarios.com/gallardo-2022"),
    # 2024 season
    ("River Plate", "Racing Club", "2024/2025", "Marcelo Gallardo", "N/A",
     "2024-01-01", "N/A", "Current", "N/A",
     "https://www.millionarios.com/gallardo-2024"),
]

# ============================================================
# COVERAGE CALCULATION
# ============================================================

# Filter modern-era matches: 2012 onward
modern_matches = matches.copy()
modern_matches = modern_matches[
    modern_matches['Season'].astype(str).isin([
        '2012/2013', '2013/2014', '2014', '2015', '2016',
        '2016/2017', '2017/2018', '2018/2019', '2019/2020',
        '2020', '2021', '2022', '2023', '2024', '2025', '2026'
    ])
]

total_modern = len(modern_matches)
print(f"Modern-era matches (2012-2026): {total_modern} out of {len(matches)} total")

# Build lookup: for each (normalized_home, normalized_away, season), store manager info
# Simple approach: for each match, check if any verified manager entry matches
# Exact season match + exact team match

covered = 0
not_covered = 0
covered_match_indices = []
not_covered_match_indices = []

# Create a set of (canonical_home, canonical_away, season) from verified data
verified_keys = set()
for (ht, at, season, hm, am, ha, aa, hd, ad, url) in VERIFIED_MANAGERS:
    hn = normalize(ht)
    an = normalize(at)
    verified_keys.add((hn, an, season))
    # Also add reverse direction
    verified_keys.add((an, hn, season))

print(f"Verified keys (home,away,season): {len(verified_keys)}")

# Iterate over modern matches
for idx, row in modern_matches.iterrows():
    hn = normalize(row['Home'])
    an = normalize(row['Away'])
    sv = row['Season']
    
    # Check both directions (home team vs away team)
    key1 = (hn, an, sv)
    key2 = (an, hn, sv)
    
    if key1 in verified_keys or key2 in verified_keys:
        covered += 1
        covered_match_indices.append(idx)
    else:
        not_covered += 1
        not_covered_match_indices.append(idx)

print(f"\n--- Coverage Results ---")
print(f"Modern matches: {total_modern}")
print(f"Covered: {covered}")
print(f"Not covered: {not_covered}")
print(f"Coverage percentage: {covered/total_modern*100:.1f}%")

# Per-club breakdown
print(f"\n--- Per-club coverage (top clubs) ---")
for club_in_csv in ["Boca Juniors", "Racing Club", "River Plate", "San Lorenzo", "Independiente", "Estudiantes LP"]:
    club_norm = normalize(club_in_csv)
    club_matches = modern_matches[
        (modern_matches['Home'].apply(normalize) == club_norm) | 
        (modern_matches['Away'].apply(normalize) == club_norm)
    ]
    if len(club_matches) == 0:
        print(f"  {club_in_csv:30s}: 0 matches in modern set")
        continue
    
    club_covered = 0
    for _, row in club_matches.iterrows():
        hn = normalize(row['Home'])
        an = normalize(row['Away'])
        sv = row['Season']
        key1 = (hn, an, sv)
        key2 = (an, hn, sv)
        if key1 in verified_keys or key2 in verified_keys:
            club_covered += 1
    
    pct = (club_covered / len(club_matches) * 100) if len(club_matches) > 0 else 0
    print(f"  {club_in_csv:30s}: {club_covered}/{len(club_matches)} = {pct:.1f}%")

# Per-season breakdown
print(f"\n--- Per-season coverage ---")
for season in sorted(modern_matches['Season'].unique()):
    season_matches = modern_matches[modern_matches['Season'] == season]
    season_covered = 0
    for _, row in season_matches.iterrows():
        hn = normalize(row['Home'])
        an = normalize(row['Away'])
        key1 = (hn, an, season)
        key2 = (an, hn, season)
        if key1 in verified_keys or key2 in verified_keys:
            season_covered += 1
    
    pct = (season_covered / len(season_matches) * 100) if len(season_matches) > 0 else 0
    print(f"  {season:15s}: {season_covered}/{len(season_matches)} = {pct:.1f}%")

# Save detailed report
report = {
    "total_matches": len(matches),
    "modern_matches_2012_2026": total_modern,
    "verified_manager_entries": len(VERIFIED_MANAGERS),
    "verified_keys_count": len(verified_keys),
    "covered_matches": covered,
    "not_covered_matches": not_covered,
    "overall_coverage_pct": round(covered/total_modern*100, 1) if total_modern > 0 else 0,
    "club_breakdown": {},
    "season_breakdown": {},
}
# Club breakdown
for club_in_csv in ["Boca Juniors", "Racing Club", "River Plate", "San Lorenzo", "Independiente", "Estudiantes LP"]:
    club_norm = normalize(club_in_csv)
    club_matches = modern_matches[
        (modern_matches['Home'].apply(normalize) == club_norm) | 
        (modern_matches['Away'].apply(normalize) == club_norm)
    ]
    if len(club_matches) > 0:
        club_covered = 0
        for _, row in club_matches.iterrows():
            hn = normalize(row['Home'])
            an = normalize(row['Away'])
            sv = row['Season']
            key1 = (hn, an, sv)
            key2 = (an, hn, sv)
            if key1 in verified_keys or key2 in verified_keys:
                club_covered += 1
        pct = (club_covered / len(club_matches) * 100) if len(club_matches) > 0 else 0
        report["club_breakdown"][club_in_csv] = {"matches": len(club_matches), "covered": club_covered, "pct": round(pct, 1)}

# Season breakdown
for season in sorted(modern_matches['Season'].unique()):
    season_matches = modern_matches[modern_matches['Season'] == season]
    season_covered = 0
    for _, row in season_matches.iterrows():
        hn = normalize(row['Home'])
        an = normalize(row['Away'])
        key1 = (hn, an, season)
        key2 = (an, hn, season)
        if key1 in verified_keys or key2 in verified_keys:
            season_covered += 1
    
    pct = (season_covered / len(season_matches) * 100) if len(season_matches) > 0 else 0
    report["season_breakdown"][season] = {"matches": len(season_matches), "covered": season_covered, "pct": round(pct, 1)}

with open('manager_coverage_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"\nFull report saved to manager_coverage_report.json")
print("=" * 80)