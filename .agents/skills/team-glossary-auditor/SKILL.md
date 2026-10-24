---
name: team-glossary-auditor
description: Identifies, fuzzy-matches, and resolves team name variations across data sources (AFA, TyC Sports, FBref, FootyStats, Sofascore, football-data.co.uk) against Glossary.txt to prevent unmapped team errors.
---

# Team Glossary Auditor Skill

This skill automates the detection, validation, and resolution of team name variations across all external data feeds in `ML_Predictor2026_V2`.

## The Problem
Data providers use divergent naming schemes for Argentine teams:
- **`football-data.co.uk` (Canonical source for `ARG.csv`)**: e.g., `Independiente`, `Defensa y Justicia`, `Gimnasia L.P.`.
- **`TyC Sports`**: Nicknames and short forms (e.g., `Def y Justicia`, `Gimnasia (LP)`, `Ind Rivadavia`).
- **`FBref` / `FootyStats`**: Long official Spanish names or translated forms.
- **`Partidos.txt`**: User-entered or web-scraped fixture strings.

If a team name does not normalize to the exact canonical name in `ARG.csv`, feature generators fail to retrieve historical stats and fall back to default ratings.

---

## Audit Procedures

### 1. Audit a Fixture File (`Partidos.txt`)

Run the automated auditor script on `Partidos.txt`:
```powershell
.\.venv\Scripts\python.exe scripts/audit_team_names.py Partidos.txt
```

The script:
1. Parses all home and away team names.
2. Checks normalization through `Glossary.txt`.
3. If an alias is missing, uses fuzzy Levenshtein matching against all known canonical names in `Glossary.txt` and `ARG.csv`.
4. Outputs the exact copy-paste entry needed for `Glossary.txt`.

### 2. Audit Scraped CSV Files

To audit team names in newly scraped CSV files (e.g. from Sofascore or FBref):
```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; from scripts.audit_team_names import audit_names; df = pd.read_csv('src/fbref_league_table_20261004_0.csv'); audit_names(df['Squad'].dropna().unique())"
```

---

## Adding New Entries to `Glossary.txt`

When an unmapped team or new promoted team variant is detected:
1. Open `Glossary.txt`.
2. Locate the team's block or append at the bottom of the section.
3. Add the mapping in the canonical format:
   ```text
   Variant Name -> CANONICAL NAME
   ```
4. Example:
   ```text
   Ind Rivadavia -> Independiente Rivadavia
   Def y Justicia -> Defensa y Justicia
   Central Cba (SdE) -> Central Cordoba
   ```

### Chronic Ambiguities & Safeguards
- **"Gimnasia"**: Never map unqualified "Gimnasia" — distinguish between `Gimnasia L.P.` and `Gimnasia (Mendoza)`.
- **"Central"**: Disambiguate between `Rosario Central` and `Central Cordoba`.
- **"Independiente"**: Unqualified maps to `Independiente` (Avellaneda), NOT `Independiente Rivadavia`.
- **"Estudiantes"**: Distinguish between `Estudiantes L.P.` and `Estudiantes Rio Cuarto`.

---

## Verification

After updating `Glossary.txt`, re-run the audit to ensure all fixtures resolve cleanly:
```powershell
.\.venv\Scripts\python.exe scripts/audit_team_names.py Partidos.txt
```
*Expected Result*: `[OK] All team names successfully resolve to canonical names!`
