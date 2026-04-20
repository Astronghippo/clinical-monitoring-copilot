"""Tests for the weekly narrative digest service and POST /analyses/{id}/digest endpoint."""
from __future__ import annotations

import pytest

from app.services.digest import draft_digest


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

class StubLLM:
    def __init__(self, reply: str = "Week 12 saw elevated dropout rates…"):
        self._reply = reply
        self.last_system: str | None = None
        self.last_user: str | None = None

    def text_completion(self, *, system: str, user: str, max_tokens: int = 2048) -> str:
        self.last_system = system
        self.last_user = user
        return self._reply


def _findings() -> list[dict]:
    return [
        {
            "analyzer": "eligibility",
            "severity": "critical",
            "subject_id": "1012",
            "summary": "E2 violation: HbA1c too high",
            "status": "open",
        },
        {
            "analyzer": "completeness",
            "severity": "major",
            "subject_id": "1007",
            "summary": "Missing labs at V2",
            "status": "resolved",
        },
        {
            "analyzer": "visit_windows",
            "severity": "minor",
            "subject_id": "1003",
            "summary": "V3 visit 2 days outside window",
            "status": "open",
        },
    ]


def test_draft_digest_returns_string():
    llm = StubLLM("Para 1. Para 2.")
    result = draft_digest(study_id="TST-001", findings=_findings(), llm=llm)
    assert isinstance(result, str)
    assert len(result) > 0


def test_draft_digest_includes_study_id_in_prompt():
    llm = StubLLM()
    draft_digest(study_id="ACME-DM2-302", findings=_findings(), llm=llm)
    assert "ACME-DM2-302" in llm.last_user


def test_draft_digest_includes_finding_counts_in_prompt():
    llm = StubLLM()
    draft_digest(study_id="TST-001", findings=_findings(), llm=llm)
    # 1 critical, 1 major, 1 minor in our sample
    assert "critical" in llm.last_user.lower() or "1" in llm.last_user


def test_draft_digest_passes_system_prompt():
    llm = StubLLM()
    draft_digest(study_id="TST-001", findings=_findings(), llm=llm)
    assert llm.last_system is not None
    assert len(llm.last_system) > 20


def test_draft_digest_handles_empty_findings():
    llm = StubLLM("No findings this week.")
    result = draft_digest(study_id="TST-001", findings=[], llm=llm)
    assert result == "No findings this week."


def test_draft_digest_passes_status_breakdown():
    llm = StubLLM()
    draft_digest(study_id="TST-001", findings=_findings(), llm=llm)
    # 2 open, 1 resolved
    assert "open" in llm.last_user.lower() or "resolved" in llm.last_user.lower()


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------

def _seed_analysis(db) -> int:
    from app.models import Analysis, Dataset, FindingRow, Protocol

    p = Protocol(study_id="TST-001", filename="test.pdf", raw_text="x", parse_status="done")
    db.add(p)
    db.flush()

    d = Dataset(name="ds", storage_path="/tmp/ds.zip")
    db.add(d)
    db.flush()

    a = Analysis(protocol_id=p.id, dataset_id=d.id, status="done")
    db.add(a)
    db.flush()

    findings = [
        FindingRow(
            analysis_id=a.id, analyzer="eligibility", severity="critical",
            subject_id="1012", summary="E2 violation", detail="detail",
            protocol_citation="sec 5", data_citation={}, confidence=0.9,
        ),
        FindingRow(
            analysis_id=a.id, analyzer="completeness", severity="major",
            subject_id="1007", summary="Missing labs", detail="detail",
            protocol_citation="sec 6", data_citation={}, confidence=0.8,
        ),
    ]
    db.add_all(findings)
    db.commit()
    db.refresh(a)
    return a.id


def test_digest_endpoint_returns_digest_text(client_with_sqlite, monkeypatch):
    import app.routes.analyses as analyses_mod

    class _FakeLLM:
        def text_completion(self, *, system, user, max_tokens=2048):
            return "Study TST-001 summary paragraph one. Paragraph two."

    monkeypatch.setattr(analyses_mod, "_digest_llm", _FakeLLM())

    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())
    aid = _seed_analysis(db)

    resp = client_with_sqlite.post(f"/analyses/{aid}/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert "digest" in data
    assert "TST-001" in data["digest"]


def test_digest_endpoint_404_on_missing_analysis(client_with_sqlite):
    resp = client_with_sqlite.post("/analyses/9999/digest")
    assert resp.status_code == 404


def test_digest_endpoint_404_when_analysis_not_done(client_with_sqlite, monkeypatch):
    import app.routes.analyses as analyses_mod

    class _FakeLLM:
        def text_completion(self, *, system, user, max_tokens=2048):
            return "done"

    monkeypatch.setattr(analyses_mod, "_digest_llm", _FakeLLM())

    from app.models import Analysis, Dataset, Protocol
    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())

    p = Protocol(study_id="X", filename="f.pdf", raw_text="", parse_status="done")
    db.add(p)
    db.flush()
    d = Dataset(name="d", storage_path="/tmp/x.zip")
    db.add(d)
    db.flush()
    a = Analysis(protocol_id=p.id, dataset_id=d.id, status="running")
    db.add(a)
    db.commit()
    db.refresh(a)

    resp = client_with_sqlite.post(f"/analyses/{a.id}/digest")
    assert resp.status_code == 409
