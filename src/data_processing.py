# Data loading and normalization

import json
import os
import re
import pandas as pd
from src.utils import log_info, log_ok, log_error, log_warning

def load_glossary(filepath="Glossary.txt"):
    """Load team name mappings from Glossary.txt."""
    glossary = {}
    if not os.path.exists(filepath):
        log_warning(f"Glossary file not found: {filepath}")
        return glossary

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Support multiple delimiters: ->, =, :
                parts = None
                for delim in ["->", "=", ":"]:
                    if delim in line:
                        parts = line.split(delim, 1)
                        break
                
                if parts and len(parts) == 2:
                    source = parts[0].strip().upper()
                    target = parts[1].strip().upper()
                    glossary[source] = target
        log_ok(f"Loaded {len(glossary)} team name mappings from glossary")
    except Exception as e:
        log_error(f"Error reading glossary: {e}")
    return glossary

def normalize_team_name(name, glossary=None):
    """Normalize team names for consistent merging."""
    if not name or pd.isna(name):
        return ""
        
    # Initial cleanup: strip, upper, and basic character replacement
    name = str(name).strip().upper()
    
    # Common variations mapping (internal glossary)
    INTERNAL_MAPPING = {
        "CENTRAL CORDOBA (SGO)": "CENTRAL CORDOBA",
        "CENTRAL CORDOBA SDE": "CENTRAL CORDOBA",
        "CENTRAL CBA": "CENTRAL CORDOBA",
        "ESTUDIANTES": "ESTUDIANTES LP",
        "ESTUDIANTES DE LA PLATA": "ESTUDIANTES LP",
        "ESTUDIANTES (LP)": "ESTUDIANTES LP",
        "GIMNASIA": "GIMNASIA LP",
        "GIMNASIA Y ESGRIMA": "GIMNASIA LP",
        "GIMNASIA (LP)": "GIMNASIA LP",
        "GIMNASIA DE LA PLATA": "GIMNASIA LP",
        "GIMNASIA MZA": "GIMNASIA MENDOZA",
        "GIMNASIA (M)": "GIMNASIA MENDOZA",
        "GIMNASIA Y ESGRIMA (M)": "GIMNASIA MENDOZA",
        "INSTITUTO ACC": "INSTITUTO",
        "INSTITUTO (C)": "INSTITUTO",
        "NEWELLS": "NEWELLS OLD BOYS",
        "NEWELLS OLD BOYS (ROS)": "NEWELLS OLD BOYS",
        "NOB": "NEWELLS OLD BOYS",
        "ROSARIO": "ROSARIO CENTRAL",
        "R CENTRAL": "ROSARIO CENTRAL",
        "TALLERES": "TALLERES CORDOBA",
        "TALLERES (C)": "TALLERES CORDOBA",
        "TALLERES DE CORDOBA": "TALLERES CORDOBA",
        "UNION": "UNION DE SANTA FE",
        "UNION SF": "UNION DE SANTA FE",
        "DEFENSA": "DEFENSA Y JUSTICIA",
        "DYJ": "DEFENSA Y JUSTICIA",
        "ATL": "ATL TUCUMAN",
        "ATL TUC": "ATL TUCUMAN",
        "TUCUMAN": "ATL TUCUMAN",
        "IND RIVADAVIA": "INDEPENDIENTE RIVADAVIA",
        "IND RIV": "INDEPENDIENTE RIVADAVIA",
        "DEP RIESTRA": "DEPORTIVO RIESTRA",
        "RIESTRA": "DEPORTIVO RIESTRA",
        "BARRACAS": "BARRACAS CENTRAL",
        "SARMIENTO": "SARMIENTO JUNIN",
        "SARMIENTO (J)": "SARMIENTO JUNIN",
    }
    
    if name in INTERNAL_MAPPING:
        name = INTERNAL_MAPPING[name]
        
    # Apply user glossary mapping if available (overrides internal)
    if glossary and name in glossary:
        name = glossary[name]
        
    # Consistent character normalization
    name = name.replace(".", "").replace("-", " ").replace("–", " ").replace("—", " ")
    
    # Remove accents
    mapping = str.maketrans({
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N",
        "á": "A", "é": "E", "í": "I", "ó": "O", "ú": "U", "ü": "U", "ñ": "N"
    })
    name = name.translate(mapping)
    
    # Remove multiple spaces and keep only A-Z and spaces
    name = re.sub(r"[^A-Z ]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    
    return name

def load_sofascore_data(filepath="src/sofascore_stats.json", glossary=None):
    """Load Sofascore standings data from JSON file."""
    sofascore_data = {}
    if not os.path.exists(filepath):
        log_warning(f"Sofascore data file not found: {filepath}")
        return sofascore_data

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        teams_list = data.get("teams", [])
        if not teams_list:
            log_warning("No teams found in Sofascore data")
            return sofascore_data

        # Handle different possible JSON structures
        for team in teams_list:
            # Structure 1: Nested standings rows
            if "standings" in team:
                for standing_type in team.get("standings", []):
                    for idx, row in enumerate(standing_type.get("rows", [])):
                        team_info = row.get("team", {})
                        name = team_info.get("name", "")
                        if name:
                            normalized = normalize_team_name(name, glossary)
                            sofascore_data[normalized] = _extract_sofa_stats(row, idx + 1)
                continue # Processed nested structure

            # Structure 2: Flattened team objects
            name = team.get("name") or team.get("normalized")
            if name:
                normalized = normalize_team_name(name, glossary)
                sofascore_data[normalized] = {
                    "position": team.get("position", 0),
                    "points": team.get("points", 0),
                    "played": team.get("played", 0),
                    "won": team.get("won", 0),
                    "drawn": team.get("drawn", 0),
                    "lost": team.get("lost", 0),
                    "goals_for": team.get("goals_for", team.get("goalsFor", 0)),
                    "goals_against": team.get("goals_against", team.get("goalsAgainst", 0)),
                    "goal_difference": team.get("goal_difference", team.get("goalDifference", 0)),
                    "rating": team.get("rating"),
                }
                
        log_ok(f"Loaded Sofascore data for {len(sofascore_data)} teams")
    except Exception as e:
        log_error(f"Error reading Sofascore data: {e}")
    return sofascore_data

def _extract_sofa_stats(row, position):
    """Helper to extract stats from a Sofascore row object."""
    return {
        "position": position,
        "points": row.get("points", 0),
        "played": row.get("matches", row.get("played", 0)),
        "won": row.get("wins", row.get("won", 0)),
        "drawn": row.get("draws", row.get("drawn", 0)),
        "lost": row.get("losses", row.get("lost", 0)),
        "goals_for": row.get("goalsFor", 0),
        "goals_against": row.get("goalsAgainst", 0),
        "goal_difference": row.get("goalDifference", 0),
        "rating": None,
    }

def clean_partidos_file(path: str, glossary: dict = None) -> None:
    """Normalize partidos.txt in place."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        log_error(f"Fixtures file not found: {path}")
        return

    cleaned_lines = []
    for line in lines:
        if not line.strip():
            continue
            
        # Basic character cleanup
        s = line.replace("\t", " ")
        # Handle Spanish accents
        mapping = str.maketrans({"á": "a", "Á": "A", "é": "e", "É": "E", "í": "i", "Í": "I", "ó": "o", "Ó": "O", "ú": "u", "Ú": "U", "ü": "u", "Ü": "U"})
        s = s.translate(mapping)
        s = s.replace("–", "-").replace("—", "-")
        
        # Remove special characters but keep letters, numbers, and basic punctuation
        s = re.sub(r"[^A-Za-zÑñ:\-\d ]+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        
        if s:
            cleaned_lines.append(s)
            
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))
    log_ok("Fixtures file cleaned.")

def parse_fixtures(filepath, glossary=None):
    """Parse fixture lines into a DataFrame."""
    fixtures_out = []
    if not os.path.exists(filepath):
        log_warning(f"Fixtures file not found: {filepath}")
        return pd.DataFrame()

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
                
            s_upper = s.upper()
            if s_upper.startswith("FECHA") or s_upper.startswith("CANTIDAD"):
                continue
                
            # Try to extract score if present
            m = re.search(r"(\d+)\s*[-:]\s*(\d+)", s)
            home_score, away_score = None, None
            if m:
                home_score, away_score = int(m.group(1)), int(m.group(2))
                s = re.sub(r"(\d+)\s*[-:]\s*(\d+)", "", s).strip()
            
            # Identify teams separated by hyphen
            if "-" not in s and "–" not in s:
                continue
                
            s = s.rstrip(": ").strip()
            parts = re.split(r"[-–]", s)
            if len(parts) == 2:
                raw_home = parts[0].strip()
                raw_away = parts[1].strip()
                home = normalize_team_name(raw_home, glossary)
                away = normalize_team_name(raw_away, glossary)
                fixtures_out.append({
                    "Raw_Home": raw_home,
                    "Raw_Away": raw_away,
                    "Home": home,
                    "Away": away,
                    "Home_Score": home_score,
                    "Away_Score": away_score,
                })
                
    return pd.DataFrame(fixtures_out)

def parse_results_file(filepath):
    """Parse a results file (Resultados_*.txt) into a dictionary of predictions."""
    predictions = {}
    if not os.path.exists(filepath):
        return predictions

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            current_match = None
            for line in f:
                line = line.strip()
                if " - " in line and "=" not in line and "FECHA" not in line.upper():
                    parts = line.split(" - ")
                    if len(parts) == 2:
                        # Use normalized names for keys
                        home = normalize_team_name(parts[0].strip())
                        away = normalize_team_name(parts[1].strip())
                        current_match = (home, away)
                        predictions[current_match] = {}
                elif "Resultado:" in line and current_match:
                    # Extract score and outcome
                    if "(" in line and ")" in line:
                        outcome = line[line.index("(") + 1 : line.index(")")]
                        score_part = line.replace("Resultado:", "").strip().split(" ")[0]
                        predictions[current_match]["score"] = score_part
                        predictions[current_match]["outcome"] = outcome
                elif "xG:" in line and current_match:
                    xg = line.replace("xG:", "").strip()
                    predictions[current_match]["xg"] = xg
                elif "Confianza:" in line and current_match:
                    conf = line.replace("Confianza:", "").strip()
                    predictions[current_match]["confidence"] = conf
    except Exception as e:
        log_error(f"Error parsing results file {filepath}: {e}")
    
    return predictions

def load_data(filepath, glossary=None):
    """Load and clean main dataset."""
    if not os.path.exists(filepath):
        log_error(f"Data file not found: {filepath}")
        return pd.DataFrame()
    
    # Check if file needs cleaning (basic check for non-CSV format or encoding issues)
    # For ARG.csv, we usually just load it directly
    try:
        df = pd.read_csv(filepath)
        log_ok(f"Loaded {len(df)} rows from {filepath}")
        return df
    except Exception as e:
        log_error(f"Error loading {filepath}: {e}")
        return pd.DataFrame()
