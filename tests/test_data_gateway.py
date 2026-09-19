"""Contract tests for the DataGateway + EntityResolver layer (P1 #7)."""
import pandas as pd

from src.data_gateway import DataGateway
from src.entity_resolver import EntityResolver
from src.pdf_reports import find_latest_report_pdf


def _write(path, content):
    path.write_text(content, encoding="utf-8")


# --- EntityResolver ---------------------------------------------------------

def test_entity_resolver_riestra_consistent_across_all_maps(tmp_path):
    """Glossary, API map and internal map must all yield DEP RIESTRA."""
    glossary = tmp_path / "Glossary.txt"
    _write(glossary, (
        "# DEPORTIVO RIESTRA\n"
        "Riestra -> DEP RIESTRA\n"
        "Dep. Riestra -> DEP RIESTRA\n"
        "Deportivo Riestra -> DEP RIESTRA\n"
    ))
    resolver = EntityResolver(str(glossary))

    # Glossary path
    assert resolver.resolve("Riestra") == "DEP RIESTRA"
    assert resolver.resolve("Dep. Riestra") == "DEP RIESTRA"
    # API-name layer (Deportivo Riestra is the Sofascore/API-Football spelling)
    assert resolver.resolve("Deportivo Riestra") == "DEP RIESTRA"
    assert resolver.resolve("Gimnasia L.P.") == "GIMNASIA LP"
    # Internal map fallback
    assert resolver.resolve("RIESTRA") == "DEP RIESTRA"


# --- DataGateway ------------------------------------------------------------

def test_gateway_load_matches_and_sofascore(tmp_path):
    csv = tmp_path / "ARG.csv"
    _write(csv, "Date,HomeTeam,AwayTeam,FullTimeResult\n01/01/2025,Boca Juniors,River Plate,H\n")
    gw = DataGateway(
        data_path=str(csv),
        fixtures_path=str(tmp_path / "Partidos.txt"),
        sofascore_path=str(tmp_path / "missing.json"),
        glossary_path=str(tmp_path / "Glossary.txt"),
    )

    df = gw.load_matches()
    assert list(df.columns) == ["Date", "HomeTeam", "AwayTeam", "FullTimeResult"]
    assert df["HomeTeam"].iloc[0] == "BOCA JUNIORS"
    assert df["AwayTeam"].iloc[0] == "RIVER PLATE"

    # Missing sofascore file is legitimately "no data" ({}), not an error
    assert gw.load_sofascore() == {}


def test_gateway_load_fixtures(tmp_path):
    fixtures = tmp_path / "Partidos.txt"
    _write(fixtures, "FECHA 10\nBoca Juniors - River Plate\n")
    gw = DataGateway(
        data_path=str(tmp_path / "ARG.csv"),
        fixtures_path=str(fixtures),
        sofascore_path=str(tmp_path / "missing.json"),
        glossary_path=str(tmp_path / "Glossary.txt"),
    )

    df, header, summary = gw.load_fixtures()
    assert header == "FECHA 10"
    assert len(df) == 1
    assert df["HomeTeam"].iloc[0] == "BOCA JUNIORS"
    assert df["AwayTeam"].iloc[0] == "RIVER PLATE"


def test_gateway_fixtures_missing_returns_empty(tmp_path):
    gw = DataGateway(
        data_path=str(tmp_path / "ARG.csv"),
        fixtures_path=str(tmp_path / "no_such.txt"),
        sofascore_path=str(tmp_path / "missing.json"),
        glossary_path=str(tmp_path / "Glossary.txt"),
    )
    df, header, summary = gw.load_fixtures()
    assert df.empty and header is None and summary["goles"] == 0


# --- pdf_reports (unified pdfplumber discovery, P1 #8) ----------------------

def test_find_latest_report_pdf(tmp_path):
    (tmp_path / "Resumen F08.pdf").write_bytes(b"x")
    (tmp_path / "Resumen F11.pdf").write_bytes(b"x")
    assert find_latest_report_pdf(str(tmp_path)).endswith("Resumen F11.pdf")
    assert find_latest_report_pdf(str(tmp_path / "empty")) is None