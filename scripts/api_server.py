"""
Liga Profesional Argentina Predictions API Server
REST API for match predictions with JSON responses
"""

import argparse
import json
import os
import sys
import glob
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.data_processing import load_glossary, normalize_team_name, parse_fixtures, parse_results_file


class DataManager:
    """Handles loading and caching of fixture and prediction data"""
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.glossary = load_glossary(os.path.join(project_dir, "Glossary.txt"))
        self._fixtures = None
        self._predictions = None
        self._last_load = 0
        self.cache_ttl = 300  # 5 minutes

    def _should_reload(self):
        return time.time() - self._last_load > self.cache_ttl

    def get_fixtures(self):
        if self._fixtures is None or self._should_reload():
            path = os.path.join(self.project_dir, "partidos.txt")
            df = parse_fixtures(path, self.glossary)
            self._fixtures = df.to_dict("records") if not df.empty else []
            self._last_load = time.time()
        return self._fixtures

    def get_predictions(self):
        if self._predictions is None or self._should_reload():
            files = glob.glob(os.path.join(self.project_dir, "Resultados_*.txt"))
            if not files:
                self._predictions = {}
            else:
                latest = max(files)
                self._predictions = parse_results_file(latest)
            self._last_load = time.time()
        return self._predictions


# Global data manager
data_manager = DataManager(PROJECT_DIR)


class PredictionHandler(BaseHTTPRequestHandler):
    """HTTP request handler for predictions API"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def send_json(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode())

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        routes = {
            "/predictions": self.handle_predictions,
            "/": self.handle_predictions,
            "/teams": self.handle_teams,
            "/stats": self.handle_stats,
            "/health": lambda _: self.send_json({"status": "ok"})
        }

        handler = routes.get(path)
        if handler:
            try:
                handler(params)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_json({"error": "Not found"}, 404)

    def handle_predictions(self, params):
        """Get match predictions"""
        fixtures = data_manager.get_fixtures()
        predictions = data_manager.get_predictions()

        # Filter by params
        home_filter = params.get("home", [None])[0]
        away_filter = params.get("away", [None])[0]
        matchweek_filter = params.get("matchweek", [None])[0]

        matches = []
        for f in fixtures:
            h_norm = f["Home"]
            a_norm = f["Away"]
            
            if home_filter and home_filter.upper() not in h_norm:
                continue
            if away_filter and away_filter.upper() not in a_norm:
                continue

            # Find prediction
            pred = predictions.get((h_norm, a_norm), {})

            match = {
                "home_team": f["Raw_Home"],
                "away_team": f["Raw_Away"],
                "home_normalized": h_norm,
                "away_normalized": a_norm,
                "predictions": {
                    "score": pred.get("score", "TBD"),
                    "outcome": pred.get("outcome", "TBD"),
                    "xg": pred.get("xg", "TBD"),
                    "confidence": pred.get("confidence", "TBD")
                }
            }
            matches.append(match)

        response = {
            "league": "Liga Profesional Argentina",
            "matchweek": matchweek_filter or "current",
            "count": len(matches),
            "matches": matches
        }
        self.send_json(response)

    def handle_teams(self, _):
        """List all teams from fixtures"""
        fixtures = data_manager.get_fixtures()
        teams = set()
        for f in fixtures:
            teams.add(f["Home"])
            teams.add(f["Away"])
        
        self.send_json({"teams": sorted(list(teams))})

    def handle_stats(self, _):
        """Get model statistics"""
        self.send_json({
            "model": "CatBoost + Poisson V2",
            "accuracy": 0.421,
            "log_loss": 1.090,
            "features": 21,
            "training_samples": 6049,
            "league": "Liga Profesional Argentina"
        })


def run_server(port=8080):
    """Run the API server"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, PredictionHandler)
    print(f"Server running on http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_server(args.port)
