#!/usr/bin/env bash
set -euo pipefail

# Security Manifest:
#   Environment variables: none
#   External endpoints: optional Apify API for Sofascore data
#   Local files accessed: main.py, src/*, data/ARG.csv, partidos.txt
#   Data sent: team names and match data (no PII)

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/.venv/Scripts/python.exe"
PYTHON="${VENV_PYTHON:-$PROJECT_DIR/python}"

# Check for virtual environment
if [[ -f "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
fi

usage() {
    cat <<'EOF'
Usage: liga_argentina.sh <command>

Commands:
  predict    Generate predictions for current fixtures
  run        Run full pipeline (scrape data + predict)
  results    Show most recent prediction results
  stats      Show model accuracy metrics
  help       Display this help message

Examples:
  liga_argentina.sh predict
  liga_argentina.sh run
  liga_argentina.sh results

League: Liga Profesional Argentina
EOF
    exit 1
}

# Change to project directory
cd "$PROJECT_DIR"

# Ensure virtual environment is activated
activate_venv() {
    if [[ -f "$PROJECT_DIR/.venv/Scripts/Activate.ps1" ]]; then
        export VIRTUAL_ENV="$PROJECT_DIR/.venv"
        export PATH="$VIRTUAL_ENV/Scripts:$PATH"
    fi
}

# Run main prediction model
cmd_predict() {
    activate_venv
    echo "Running prediction model..."
    "$PYTHON" main.py
    echo ""

    # Find and display the most recent results file
    local latest_result
    latest_result=$(ls -t Resultados_*.txt 2>/dev/null | head -1)
    if [[ -n "$latest_result" && -f "$latest_result" ]]; then
        echo "============================================================"
        echo "LATEST PREDICTIONS"
        echo "============================================================"
        cat "$latest_result"
    fi
}

# Run full pipeline with data scraping
cmd_run() {
    activate_venv
    echo "Running full pipeline with data scraping..."

    echo ""
    echo "--- Scraping TyC Sports (fixtures) ---"
    "$PYTHON" scrape_tyc.py

    echo ""
    echo "--- Scraping Sofascore (standings) ---"
    "$PYTHON" scrape_sofascore_apify.py

    echo ""
    echo "--- Running prediction model ---"
    cmd_predict
}

# Show recent results
cmd_results() {
    local latest_result
    latest_result=$(ls -t Resultados_*.txt 2>/dev/null | head -1)

    if [[ -n "$latest_result" && -f "$latest_result" ]]; then
        echo "============================================================"
        echo "PREDICTIONS: $latest_result"
        echo "============================================================"
        cat "$latest_result"
    else
        echo "No prediction results found."
        echo "Run 'liga_argentina.sh run' to generate predictions."
        exit 1
    fi
}

# Show model statistics
cmd_stats() {
    activate_venv

    # Run model to get fresh stats
    echo "Running model for statistics..."
    "$PYTHON" -c "
import pandas as pd
from src.config import BASE_ELO, MODEL_TYPE, TRAILING_WINDOW, RESULT_ENCODING
from src.data_processing import load_glossary, normalize_team_name
from src.stats_engine import calculate_all_elo_ratings
from src.features import compute_trailing_features

glossary = load_glossary('Glossary.txt')
matches = pd.read_csv('data/ARG.csv')
matches = matches.dropna(subset=['Home', 'Away', 'Res', 'Date'])
matches['Date'] = pd.to_datetime(matches['Date'], dayfirst=True, errors='coerce')
matches['Home'] = matches['Home'].map(lambda x: normalize_team_name(x, glossary))
matches['Away'] = matches['Away'].map(lambda x: normalize_team_name(x, glossary))
matches['Res'] = matches['Res'].map(RESULT_ENCODING)
matches = matches.sort_values('Date').reset_index(drop=True)

elo_ratings, elo_history = calculate_all_elo_ratings(matches, BASE_ELO)
matches = compute_trailing_features(matches, window=TRAILING_WINDOW)

print(f'Model Type: {MODEL_TYPE}')
print(f'Training Samples: {len(matches)}')
print(f'Trailing Window: {TRAILING_WINDOW} matches')
print(f'Teams with Elo: {len(elo_ratings)}')
"
}

# Main dispatch
if [[ $# -lt 1 ]]; then
    usage
fi

command="$1"

case "$command" in
    predict)
        cmd_predict
        ;;
    run)
        cmd_run
        ;;
    results)
        cmd_results
        ;;
    stats)
        cmd_stats
        ;;
    help|--help|-h)
        usage
        exit 0
        ;;
    *)
        echo "Unknown command: $command" >&2
        usage
        ;;
esac
