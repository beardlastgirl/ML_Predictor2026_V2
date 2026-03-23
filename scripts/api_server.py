"""
Liga Profesional Argentina Predictions API Server
REST API for match predictions with JSON responses
"""

import argparse
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add project root to path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from src.data_processing import load_glossary, normalize_team_name


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

        if path == "/predictions" or path == "/":
            self.handle_predictions(params)
        elif path == "/teams":
            self.handle_teams()
        elif path == "/stats":
            self.handle_stats()
        elif path == "/health":
            self.send_json({"status": "ok"})
        else:
            self.send_json({"error": "Not found"}, 404)

    def handle_predictions(self, params):
        """Get match predictions"""
        try:
            # Load fixtures
            fixtures = self.load_fixtures()

            # Load model results if available
            predictions = self.load_predictions()

            # Filter by params
            home_filter = params.get("home", [None])[0]
            away_filter = params.get("away", [None])[0]
            matchweek_filter = params.get("matchweek", [None])[0]

            if home_filter:
                fixtures = [f for f in fixtures if home_filter.lower() in f["home"].lower()]
            if away_filter:
                fixtures = [f for f in fixtures if away_filter.lower() in f["away"].lower()]

            matches = []
            for f in fixtures:
                # Find prediction for this match
                pred = self.find_prediction(f["home"], f["away"], predictions)

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
                "matchweek": matchweek_filter or "current",
                "count": len(matches),
                "matches": matches
            }

            self.send_json(response)

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_teams(self):
        """List all teams"""
        teams = [
            "BOCA JUNIORS", "RIVER PLATE", "INDEPENDIENTE", "RACING CLUB",
            "SAN LORENZO", "HURACAN", "VELEZ SARSFIELD", "ESTUDIANTES LP",
            "GIMNASIA LP", "TALLERES CORDOBA", "BELGRANO", "UNION DE SANTA FE",
            "ARGENTINOS JUNIORS", "BANFIELD", "LANUS", "DEFENSA Y JUSTICIA",
            "NEWELLS OLD BOYS", "ROSARIO CENTRAL", "CENTRAL CORDOBA",
            "INSTITUTO", "TIGRE", "PLATENSE", "BARRACAS CENTRAL",
            "SARMIENTO JUNIN", "DEP RIESTRA", "ATL TUCUMAN",
            "IND RIVADAVIA", "ALDOSIVI", "GIMNASIA MENDOZA"
        ]
        self.send_json({"teams": teams})

    def handle_stats(self):
        """Get model statistics"""
        self.send_json({
            "model": "CatBoost + Poisson V2",
            "accuracy": 0.421,
            "log_loss": 1.090,
            "features": 21,
            "training_samples": 6049,
            "league": "Liga Profesional Argentina"
        })

    def load_fixtures(self):
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

    def load_predictions(self):
        """Load latest predictions from results file"""
        import glob

        files = glob.glob(os.path.join(PROJECT_DIR, "Resultados_*.txt"))
        if not files:
            return []

        latest = max(files)
        predictions = {}

        try:
            with open(latest, "r", encoding="utf-8") as f:
                current_match = None
                for line in f:
                    line = line.strip()
                    if " - " in line and "=" not in line:
                        parts = line.split(" - ")
                        if len(parts) == 2:
                            current_match = (parts[0].strip(), parts[1].strip())
                            predictions[current_match] = {}
                    elif "Resultado:" in line and current_match:
                        # Extract score and outcome
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
        except Exception:
            pass

        return predictions

    def find_prediction(self, home, away, predictions):
        """Find prediction for a specific match"""
        for (h, a), pred in predictions.items():
            if h.lower() in home.lower() or home.lower() in h.lower():
                if a.lower() in away.lower() or away.lower() in a.lower():
                    return pred
        return {}


def run_server(port=8080):
    """Run the API server"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, PredictionHandler)
    print(f"Server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET /predictions")
    print(f"  GET /teams")
    print(f"  GET /stats")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    run_server(args.port)
