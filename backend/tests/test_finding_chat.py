"""Tests for the finding chat service and POST /findings/{id}/chat endpoint."""
from __future__ import annotations

import pytest

from app.services.finding_chat import chat_with_finding


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

class StubLLM:
    def __init__(self, reply: str = "The finding was flagged because …"):
        self._reply = reply
        self.last_system: str | None = None
        self.last_messages: list | None = None

    def chat_completion(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        self.last_system = system
        self.last_messages = messages
        return self._reply


def _finding() -> dict:
    return {
        "id": 7,
        "analyzer": "eligibility",
        "severity": "critical",
        "subject_id": "1012",
        "summary": "E2 violation: HbA1c too high",
        "detail": "HbA1c 11.2% exceeds maximum of 10.5%.",
        "protocol_citation": "Eligibility Criteria, Section 5.2, Criterion E2",
        "data_citation": {"domain": "LB", "usubjid": "1012", "lbtestcd": "HBA1C"},
        "confidence": 0.95,
    }


def test_chat_returns_reply_string():
    llm = StubLLM("It was flagged because HbA1c exceeded the eligibility cutoff.")
    result = chat_with_finding(
        finding=_finding(),
        message="Why was this flagged?",
        history=[],
        llm=llm,
    )
    assert result == "It was flagged because HbA1c exceeded the eligibility cutoff."


def test_chat_includes_finding_context_in_system_prompt():
    llm = StubLLM()
    chat_with_finding(finding=_finding(), message="Why?", history=[], llm=llm)
    assert llm.last_system is not None
    assert "1012" in llm.last_system  # subject_id embedded
    assert "E2 violation" in llm.last_system  # summary embedded
    assert "HbA1c 11.2%" in llm.last_system  # detail embedded


def test_chat_appends_user_message_to_conversation():
    llm = StubLLM()
    chat_with_finding(finding=_finding(), message="What next step?", history=[], llm=llm)
    assert llm.last_messages is not None
    last_user_msg = llm.last_messages[-1]
    assert last_user_msg["role"] == "user"
    assert last_user_msg["content"] == "What next step?"


def test_chat_preserves_history_in_messages():
    llm = StubLLM()
    history = [
        {"role": "user", "content": "Why flagged?"},
        {"role": "assistant", "content": "Because HbA1c too high."},
    ]
    chat_with_finding(finding=_finding(), message="What data supports it?", history=history, llm=llm)
    assert llm.last_messages[0]["role"] == "user"
    assert llm.last_messages[1]["role"] == "assistant"
    assert llm.last_messages[2]["role"] == "user"
    assert llm.last_messages[2]["content"] == "What data supports it?"


def test_chat_empty_history_allowed():
    llm = StubLLM("OK")
    result = chat_with_finding(finding=_finding(), message="Hello", history=[], llm=llm)
    assert result == "OK"


# ---------------------------------------------------------------------------
# HTTP endpoint tests
# ---------------------------------------------------------------------------

def _seed_finding(db):
    """Insert a minimal Analysis + FindingRow and return the finding id."""
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

    f = FindingRow(
        analysis_id=a.id,
        analyzer="eligibility",
        severity="critical",
        subject_id="1012",
        summary="E2 violation: HbA1c too high",
        detail="HbA1c 11.2% exceeds maximum of 10.5%.",
        protocol_citation="Section 5.2",
        data_citation={"domain": "LB"},
        confidence=0.95,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f.id


def test_chat_endpoint_returns_reply(client_with_sqlite, monkeypatch):
    import app.routes.findings as findings_mod

    class _FakeLLM:
        def chat_completion(self, *, system, messages, max_tokens=1024):
            return "Great question — here is why."

    monkeypatch.setattr(findings_mod, "_chat_llm", _FakeLLM())

    # Seed DB
    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())
    fid = _seed_finding(db)

    resp = client_with_sqlite.post(
        f"/findings/{fid}/chat",
        json={"message": "Why was this flagged?", "history": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Great question — here is why."


def test_chat_endpoint_404_on_missing_finding(client_with_sqlite):
    resp = client_with_sqlite.post(
        "/findings/9999/chat",
        json={"message": "hello", "history": []},
    )
    assert resp.status_code == 404


def test_chat_endpoint_passes_history_through(client_with_sqlite, monkeypatch):
    import app.routes.findings as findings_mod

    captured: dict = {}

    class _CaptureLLM:
        def chat_completion(self, *, system, messages, max_tokens=1024):
            captured["messages"] = messages
            return "reply"

    monkeypatch.setattr(findings_mod, "_chat_llm", _CaptureLLM())

    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())
    fid = _seed_finding(db)

    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
    ]
    client_with_sqlite.post(
        f"/findings/{fid}/chat",
        json={"message": "Follow-up", "history": history},
    )
    assert captured["messages"][0]["content"] == "First question"
    assert captured["messages"][-1]["content"] == "Follow-up"
