---
name: liga-argentina-predictions-api
description: REST API for AI-powered match predictions for Liga Profesional Argentina. Provides JSON endpoints for predictions including scores, expected goals, and match outcomes.
metadata: {"clawdbot":{"emoji":"soccer","requires":{"bins":["python"],"files":["scripts/*"]}}}
---

# Liga Profesional Argentina Predictions API

A REST API service for getting AI-powered predictions for Liga Profesional Argentina matches.

## Quick Start

### Start the API server
```bash
scripts/server.sh start
```

### Get predictions
```bash
scripts/server.sh predict
scripts/server.sh predict --matchweek 10
scripts/server.sh predict --home "Boca" --away "River"
```

### Stop the server
```bash
scripts/server.sh stop
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predictions` | GET | Get all predictions for current matchweek |
| `/predictions?matchweek=N` | GET | Get predictions for specific matchweek |
| `/predictions?home=TEAM` | GET | Filter by home team |
| `/predictions?away=TEAM` | GET | Filter by away team |
| `/teams` | GET | List all teams |
| `/stats` | GET | Get model statistics |

## Response Format

```json
{
  "league": "Liga Profesional Argentina",
  "matchweek": 10,
  "count": 15,
  "matches": [
    {
      "home_team": "Boca Juniors",
      "away_team": "River Plate",
      "kickoff": "2026-03-15T20:00:00",
      "predictions": [
        {"type": "score", "value": "2-1"},
        {"type": "outcome", "value": "Home Win"},
        {"type": "xg", "value": "1.65 - 1.10"},
        {"type": "confidence", "value": "High"}
      ],
      "key_players": [
        {"player_name": "Edinson Cavani", "reason": "Top scorer form"}
      ]
    }
  ]
}
```

## Running as a Service

### Start server (default port 8080)
```bash
scripts/server.sh start
scripts/server.sh start --port 9000
```

### Check server status
```bash
scripts/server.sh status
```

### Stop server
```bash
scripts/server.sh stop
```

## Configuration

- **Default Port**: 8080
- **Host**: localhost
- **Data Refresh**: Run `scripts/refresh.sh` to update predictions

## Requirements

- Python 3.8+
- Flask (for API server)
- See `requirements.txt` for ML dependencies
