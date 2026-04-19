"""Tests for the GET /analyses/{id}/sites endpoint.

TDD: tests are written before the implementation.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.models import Analysis, Dataset, FindingRow, Protocol
from app.db import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile


# ---------------------------------------------------------------------------
# Minimal fixture helpers
# ---------------------------------------------------------------------------

def _make_dataset(tmp_path: Path) -> PatientDataset:
    """Build a tiny in-memory PatientDataset for use in mocks."""
    from app.services.dataset_loader import PatientDataset
    dm = pd.DataFrame({
        "USUBJID": ["1001", "1002", "1003", "1004"],
        "SITEID":  ["SITE01", "SITE01", "SITE02", "SITE02"],
        "AGE": [40, 50, 60, 70],
    })
    sv = pd.DataFrame({"USUBJID": ["1001"], "VISIT": ["Baseline"], "VISITNUM": [1], "SVSTDTC": ["2025-01-01"]})
    vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    return PatientDataset(dm=dm, sv=sv, vs=vs)


def _db_with_data(db_path: str, findings_specs: list[dict]) -> tuple:
    """Return (engine, session_factory) seeded with a protocol, dataset, analysis,
    and FindingRows described by `findings_specs` (list of {subject_id, severity})."""
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    proto = Protocol(study_id="STUDY-X", filename="p.pdf", parse_status="done")
    db.add(proto)
    db.flush()
    ds = Dataset(name="ds", storage_path="/fake/path")
    db.add(ds)
    db.flush()
    analysis = Analysis(protocol_id=proto.id, dataset_id=ds.id, status="done")
    db.add(analysis)
    db.flush()
    for spec in findings_specs:
        db.add(FindingRow(
            analysis_id=analysis.id,
            analyzer="visit_windows",
            severity=spec["severity"],
            subject_id=spec["subject_id"],
            summary="test finding",
            detail="detail",
            protocol_citation="§1",
            data_citation={},
            confidence=0.9,
        ))
    db.commit()
    analysis_id = analysis.id
    db.close()
    return engine, Session, analysis_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def site_client(tmp_path):
    """TestClient with a fresh SQLite DB seeded with 2 sites, 4 subjects, 5 findings."""
    findings = [
        {"subject_id": "1001", "severity": "critical"},   # SITE01
        {"subject_id": "1001", "severity": "major"},       # SITE01
        {"subject_id": "1002", "severity": "minor"},       # SITE01
        {"subject_id": "1003", "severity": "major"},       # SITE02
        {"subject_id": "1004", "severity": "critical"},    # SITE02
    ]
    db_path = str(tmp_path / "test.db")
    engine, Session, analysis_id = _db_with_data(db_path, findings)
    ds_mock = _make_dataset(tmp_path)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    from app.main import app
    app.dependency_overrides[get_db] = override_db

    with patch("app.routes.analyses.load_dataset", return_value=ds_mock):
        client = TestClient(app)
        yield client, analysis_id

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sites_returns_200(site_client):
    client, aid = site_client
    r = client.get(f"/analyses/{aid}/sites")
    assert r.status_code == 200


def test_sites_schema(site_client):
    """Each item has the expected keys with correct types."""
    client, aid = site_client
    items = client.get(f"/analyses/{aid}/sites").json()
    assert len(items) == 2
    for item in items:
        assert "site_id" in item
        assert "subject_count" in item
        assert "finding_count" in item
        assert "deviation_rate" in item
        assert "counts" in item
        assert set(item["counts"].keys()) == {"critical", "major", "minor"}


def test_sites_subject_counts(site_client):
    """Each site has the correct number of subjects."""
    client, aid = site_client
    items = client.get(f"/analyses/{aid}/sites").json()
    by_site = {i["site_id"]: i for i in items}
    assert by_site["SITE01"]["subject_count"] == 2
    assert by_site["SITE02"]["subject_count"] == 2


def test_sites_finding_counts(site_client):
    """Findings are grouped correctly per site."""
    client, aid = site_client
    items = client.get(f"/analyses/{aid}/sites").json()
    by_site = {i["site_id"]: i for i in items}
    assert by_site["SITE01"]["finding_count"] == 3  # 1001×2 + 1002×1
    assert by_site["SITE02"]["finding_count"] == 2  # 1003×1 + 1004×1


def test_sites_severity_breakdown(site_client):
    """Severity counts are correct."""
    client, aid = site_client
    items = client.get(f"/analyses/{aid}/sites").json()
    by_site = {i["site_id"]: i for i in items}
    s01 = by_site["SITE01"]["counts"]
    assert s01["critical"] == 1
    assert s01["major"] == 1
    assert s01["minor"] == 1
    s02 = by_site["SITE02"]["counts"]
    assert s02["critical"] == 1
    assert s02["major"] == 1
    assert s02["minor"] == 0


def test_sites_deviation_rate(site_client):
    """deviation_rate = finding_count / subject_count."""
    client, aid = site_client
    items = client.get(f"/analyses/{aid}/sites").json()
    by_site = {i["site_id"]: i for i in items}
    assert by_site["SITE01"]["deviation_rate"] == pytest.approx(1.5)
    assert by_site["SITE02"]["deviation_rate"] == pytest.approx(1.0)


def test_sites_unknown_siteid(tmp_path):
    """Subjects with no SITEID in demographics → grouped under 'UNKNOWN'."""
    from app.services.dataset_loader import PatientDataset
    from app.main import app

    findings = [
        {"subject_id": "9999", "severity": "minor"},
    ]
    db_path = str(tmp_path / "unknown_test.db")
    engine, Session, analysis_id = _db_with_data(db_path, findings)

    # Dataset with no SITEID column
    dm = pd.DataFrame({"USUBJID": ["9999"], "AGE": [30]})
    sv = pd.DataFrame({"USUBJID": ["9999"], "VISIT": ["BL"], "VISITNUM": [1], "SVSTDTC": ["2025-01-01"]})
    vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ds_mock = PatientDataset(dm=dm, sv=sv, vs=vs)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with patch("app.routes.analyses.load_dataset", return_value=ds_mock):
        client = TestClient(app)
        r = client.get(f"/analyses/{analysis_id}/sites")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    items = r.json()
    site_ids = [i["site_id"] for i in items]
    assert "UNKNOWN" in site_ids


def test_sites_404_for_missing_analysis(site_client):
    client, _ = site_client
    r = client.get("/analyses/99999/sites")
    assert r.status_code == 404
