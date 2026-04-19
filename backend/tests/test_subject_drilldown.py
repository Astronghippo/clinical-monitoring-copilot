"""Tests for GET /analyses/{analysis_id}/subjects/{subject_id} endpoint.

TDD: tests written before implementation.
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Analysis, Dataset, FindingRow, Protocol
from app.services.dataset_loader import PatientDataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dataset(subjects=("1001", "1002"), visits=None) -> PatientDataset:
    """Build a tiny in-memory PatientDataset for mocking load_dataset."""
    if visits is None:
        visits = [
            ("1001", "Baseline", 1, "2025-01-01"),
            ("1001", "Week 4", 2, "2025-01-29"),
            ("1001", "Week 8", 3, "2025-02-26"),
            ("1002", "Baseline", 1, "2025-01-05"),
        ]
    dm = pd.DataFrame({
        "USUBJID": list({v[0] for v in visits} | set(subjects)),
        "SITEID": ["SITE01"] * len(list({v[0] for v in visits} | set(subjects))),
        "AGE": [40] * len(list({v[0] for v in visits} | set(subjects))),
    })
    sv = pd.DataFrame({
        "USUBJID": [v[0] for v in visits],
        "VISIT": [v[1] for v in visits],
        "VISITNUM": [v[2] for v in visits],
        "SVSTDTC": [v[3] for v in visits],
    })
    vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    return PatientDataset(dm=dm, sv=sv, vs=vs)


def _seed_db(db_path: str, findings_specs: list[dict]) -> tuple:
    """Return (engine, session_factory, analysis_id) with seeded data."""
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
            analyzer=spec.get("analyzer", "visit_windows"),
            severity=spec.get("severity", "major"),
            subject_id=spec["subject_id"],
            summary=spec.get("summary", "Test finding"),
            detail=spec.get("detail", "Detail"),
            protocol_citation=spec.get("protocol_citation", "§1"),
            data_citation=spec.get("data_citation", {}),
            confidence=spec.get("confidence", 0.9),
        ))
    db.commit()
    analysis_id = analysis.id
    db.close()
    return engine, Session, analysis_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def drilldown_client(tmp_path):
    """TestClient with a seeded DB and mocked dataset."""
    findings = [
        {
            "subject_id": "1001",
            "severity": "critical",
            "summary": "Subject 1001 Baseline missing required: Labs",
            "data_citation": {"visit": "Baseline", "subject_id": "1001"},
        },
        {
            "subject_id": "1001",
            "severity": "major",
            "summary": "Subject 1001 Week 4 window deviation",
            "data_citation": {"visit": "week 4", "subject_id": "1001"},  # lowercase
        },
        {
            "subject_id": "1002",
            "severity": "minor",
            "summary": "Subject 1002 Baseline minor issue",
            "data_citation": {"visit": "Baseline"},
        },
    ]
    db_path = str(tmp_path / "test.db")
    engine, Session, analysis_id = _seed_db(db_path, findings)
    ds_mock = _make_dataset()

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    with patch("app.routes.analyses.load_dataset", return_value=ds_mock):
        client = TestClient(app)
        yield client, analysis_id

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_subject_drilldown_200(drilldown_client):
    client, aid = drilldown_client
    r = client.get(f"/analyses/{aid}/subjects/1001")
    assert r.status_code == 200


def test_subject_drilldown_returns_findings_for_subject(drilldown_client):
    """Only findings for the requested subject are returned."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    assert "findings" in data
    findings = data["findings"]
    assert len(findings) == 2
    for f in findings:
        assert f["subject_id"] == "1001"


def test_subject_drilldown_finding_schema(drilldown_client):
    """Each finding has expected fields."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    f = data["findings"][0]
    assert "id" in f
    assert "severity" in f
    assert "summary" in f
    assert "analyzer" in f
    assert "status" in f


def test_subject_drilldown_returns_visits(drilldown_client):
    """Visit list for subject is returned."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    assert "visits" in data
    visits = data["visits"]
    # 1001 has 3 visits in the mock dataset
    assert len(visits) == 3


def test_subject_drilldown_visit_schema(drilldown_client):
    """Each visit has visit_name, visit_num, date, has_finding."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    for v in data["visits"]:
        assert "visit_name" in v
        assert "visit_num" in v
        assert "date" in v
        assert "has_finding" in v


def test_subject_drilldown_has_finding_true(drilldown_client):
    """Visits with findings have has_finding=True."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    visits_by_name = {v["visit_name"]: v for v in data["visits"]}
    # Baseline and Week 4 both have findings (data_citation contains matching visit name)
    assert visits_by_name["Baseline"]["has_finding"] is True
    assert visits_by_name["Week 4"]["has_finding"] is True


def test_subject_drilldown_has_finding_false(drilldown_client):
    """Visits without findings have has_finding=False."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    visits_by_name = {v["visit_name"]: v for v in data["visits"]}
    # Week 8 has no findings
    assert visits_by_name["Week 8"]["has_finding"] is False


def test_subject_drilldown_case_insensitive_visit_match(drilldown_client):
    """has_finding matching is case-insensitive (finding has 'week 4', visit is 'Week 4')."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1001").json()
    visits_by_name = {v["visit_name"]: v for v in data["visits"]}
    assert visits_by_name["Week 4"]["has_finding"] is True


def test_subject_drilldown_404_missing_analysis(drilldown_client):
    """Non-existent analysis_id returns 404."""
    client, _ = drilldown_client
    r = client.get("/analyses/99999/subjects/1001")
    assert r.status_code == 404


def test_subject_drilldown_other_subject(drilldown_client):
    """Drilldown for a different subject only shows their findings and visits."""
    client, aid = drilldown_client
    data = client.get(f"/analyses/{aid}/subjects/1002").json()
    findings = data["findings"]
    assert len(findings) == 1
    assert findings[0]["subject_id"] == "1002"
    # 1002 has 1 visit in the mock dataset
    visits = data["visits"]
    assert len(visits) == 1
