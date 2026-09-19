"""DataGateway — single facade over the two wired data paths + refresh.

Wired sources (audit 2026-09-18: only these feed the pipeline):
  * data/ARG.csv               -- historical matches (football-data.co.uk)
  * Partidos.txt               -- upcoming fixtures (TyC scraper)
  * src/sofascore_stats.json   -- standings / xG supplement (Apify scraper)

Refresh and enrichment delegate to DataIngestor (timestamp-aware ARG.csv
download + API-Football xG/possession backfill).
"""
import os

import pandas as pd

from src.data_processing import (
    clean_partidos_file,
    load_glossary,
    load_sofascore_data,
    parse_fixtures,
)
from src.data_ingestion import DataIngestor
from src.entity_resolver import EntityResolver
from src.utils import log_error, log_warning


class DataGateway:
    """Load or refresh the three wired data sources behind one interface."""

    def __init__(
        self,
        data_path: str = "data/ARG.csv",
        fixtures_path: str = "Partidos.txt",
        sofascore_path: str = "src/sofascore_stats.json",
        glossary_path: str = "Glossary.txt",
    ):
        self.data_path = data_path
        self.fixtures_path = fixtures_path
        self.sofascore_path = sofascore_path
        self.glossary = load_glossary(glossary_path)
        self.resolver = EntityResolver(glossary_path)
        self._ingestor = DataIngestor(data_path=data_path)

    def load_matches(self) -> pd.DataFrame:
        """Read historical matches and resolve team names to canonical form."""
        if not os.path.exists(self.data_path):
            log_error(f"Data file not found: {self.data_path}")
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.data_path)
            df["HomeTeam"] = df["HomeTeam"].map(self.resolver.resolve)
            df["AwayTeam"] = df["AwayTeam"].map(self.resolver.resolve)
            return df
        except Exception as e:
            log_error(f"Error loading {self.data_path}: {e}")
            return pd.DataFrame()

    def load_fixtures(self):
        """Clean and parse Partidos.txt; returns (df, header_line, summary)."""
        if not os.path.exists(self.fixtures_path):
            log_warning(f"Fixtures file not found: {self.fixtures_path}")
            return pd.DataFrame(), None, {"penales": 0, "expulsados": 0, "goles": 0}
        clean_partidos_file(self.fixtures_path, self.glossary)
        return parse_fixtures(self.fixtures_path, self.glossary)

    def load_sofascore(self) -> dict:
        """Sofascore standings/teams data; {} when the file is missing."""
        return load_sofascore_data(self.sofascore_path, glossary=self.glossary)

    def refresh(self) -> bool:
        """Download ARG.csv when the web version is newer. False = no update."""
        return self._ingestor.update_base_data()

    def enrich(self, days_back: int = 14) -> int:
        """Backfill API-Football xG/possession for recent ARG.csv rows."""
        return self._ingestor.enrich_with_api_stats(days_back)