#!/usr/bin/env bash
set -euo pipefail

# Security Manifest:
#   Environment variables: none
#   External endpoints: optional
#   Local files accessed: app.py, data/, src/
#   Data sent: team names, match data (no PII)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up 3 levels: scripts -> skill folder -> skills -> .claude -> project root
PROJECT_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
PID_FILE="$PROJECT_DIR/api_server.pid"
LOG_FILE="$PROJECT_DIR/api_server.log"

usage() {
    cat <<'EOF'
Usage: server.sh <command> [options]

Commands:
  start           Start the API server
  stop            Stop the API server
  status          Check if server is running
  predict         Get predictions (standalone)
  refresh         Refresh prediction data

Options:
  --port N        Port number (default: 8080)

Examples:
  server.sh start
  server.sh start --port 9000
  server.sh stop
  server.sh predict --home Boca --away River
EOF
    exit 1
}

get_port() {
    local port=8080
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --port)
                port="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    echo "$port"
}

cd "$PROJECT_DIR"

# Activate virtual environment
activate_venv() {
    if [[ -f "$PROJECT_DIR/.venv/Scripts/python.exe" ]]; then
        export VIRTUAL_ENV="$PROJECT_DIR/.venv"
        export PATH="$VIRTUAL_ENV/Scripts:$PATH"
    fi
}

cmd_start() {
    local port
    port=$(get_port "$@")

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Server already running on port $port (PID: $pid)"
            exit 0
        fi
    fi

    activate_venv

    echo "Starting API server on port $port..."
    python scripts/api_server.py --port "$port" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    sleep 2

    if kill -0 "$pid" 2>/dev/null; then
        echo "Server started (PID: $pid)"
    else
        echo "Failed to start server"
        exit 1
    fi
}

cmd_stop() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            rm -f "$PID_FILE"
            echo "Server stopped"
        else
            echo "Server not running"
            rm -f "$PID_FILE"
        fi
    else
        echo "Server not running (no PID file)"
    fi
}

cmd_status() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Server running (PID: $pid)"
        else
            echo "Server not running (stale PID file)"
        fi
    else
        echo "Server not running"
    fi
}

cmd_predict() {
    activate_venv

    local home_team=""
    local away_team=""
    local matchweek=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --home)
                home_team="$2"
                shift 2
                ;;
            --away)
                away_team="$2"
                shift 2
                ;;
            --matchweek)
                matchweek="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    python scripts/api_predict.py \
        ${home_team:+"--home $home_team"} \
        ${away_team:+"--away $away_team"} \
        ${matchweek:+"--matchweek $matchweek"}
}

cmd_refresh() {
    activate_venv
    echo "Refreshing prediction data..."
    python main.py
    echo "Data refreshed"
}

# Main dispatch
if [[ $# -lt 1 ]]; then
    usage
fi

command="$1"
shift

case "$command" in
    start)
        cmd_start "$@"
        ;;
    stop)
        cmd_stop
        ;;
    status)
        cmd_status
        ;;
    predict)
        cmd_predict "$@"
        ;;
    refresh)
        cmd_refresh
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Unknown command: $command" >&2
        usage
        ;;
esac
