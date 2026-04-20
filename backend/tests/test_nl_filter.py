"""Tests for natural-language → filter params translation service and endpoint.

The service takes a free-text query like
  "show me all out-of-range labs in arm B for subjects over 60"
and returns structured filter params:
  {
    "analyzer": "plausibility",       # or null
    "severity": ["critical", "major"],# or null
    "subject_ids": [...],              # or null
    "status": ["open"],                # or null
    "search_text": "out-of-range labs" # or null
  }
"""
from __future__ import annotations

import json
import pytest


# ------------------------------------------------------------------ helpers

class StubLLM:
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_user: str | None = None
        self.last_system: str | None = None

    def json_completion(self, *, system, user, max_tokens=512):
        self.last_system = system
        self.last_user = user
        return self._payload


def _filters(**kw) -> dict:
    base = {
        "analyzer": None,
        "severity": None,
        "status": None,
        "search_text": None,
    }
    base.update(kw)
    return base


# ------------------------------------------------------------------ service tests

def test_translate_query_returns_filter_dict():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters(analyzer="plausibility", severity=["critical"]))
    result = translate_query_to_filters(
        query="show out-of-range labs",
        llm=llm,
    )
    assert isinstance(result, dict)
    assert result["analyzer"] == "plausibility"


def test_translate_query_passes_query_to_llm():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters())
    translate_query_to_filters(query="critical eligibility findings", llm=llm)
    assert llm.last_user is not None
    assert "critical eligibility findings" in llm.last_user


def test_translate_query_null_fields_on_broad_query():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters())  # all None
    result = translate_query_to_filters(query="show everything", llm=llm)
    assert result["analyzer"] is None
    assert result["severity"] is None


def test_translate_query_handles_severity_list():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters(severity=["critical", "major"]))
    result = translate_query_to_filters(query="show critical and major findings", llm=llm)
    assert result["severity"] == ["critical", "major"]


def test_translate_query_handles_status_filter():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters(status=["open"]))
    result = translate_query_to_filters(query="show only open findings", llm=llm)
    assert result["status"] == ["open"]


def test_translate_query_handles_search_text():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters(search_text="HbA1c"))
    result = translate_query_to_filters(query="show HbA1c findings", llm=llm)
    assert result["search_text"] == "HbA1c"


def test_translate_query_has_system_prompt():
    from app.services.nl_filter import translate_query_to_filters

    llm = StubLLM(_filters())
    translate_query_to_filters(query="hello", llm=llm)
    assert llm.last_system is not None
    assert len(llm.last_system) > 20


# ------------------------------------------------------------------ endpoint tests

def _seed_analysis(db) -> int:
    from app.models import Analysis, Dataset, FindingRow, Protocol

    p = Protocol(study_id="TST-001", filename="p.pdf", raw_text="x", parse_status="done")
    db.add(p)
    db.flush()
    d = Dataset(name="ds", storage_path="/tmp/ds.zip")
    db.add(d)
    db.flush()
    a = Analysis(protocol_id=p.id, dataset_id=d.id, status="done")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a.id


def test_nl_filter_endpoint_returns_filter_params(client_with_sqlite, monkeypatch):
    import app.routes.analyses as analyses_mod

    class _FakeLLM:
        def json_completion(self, *, system, user, max_tokens=512):
            return {
                "analyzer": "eligibility",
                "severity": ["critical"],
                "status": None,
                "search_text": None,
            }

    monkeypatch.setattr(analyses_mod, "_nl_filter_llm", _FakeLLM())

    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())
    aid = _seed_analysis(db)

    resp = client_with_sqlite.post(
        f"/analyses/{aid}/nl-filter",
        json={"query": "show all critical eligibility findings"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["analyzer"] == "eligibility"
    assert data["severity"] == ["critical"]


def test_nl_filter_endpoint_404_on_missing_analysis(client_with_sqlite):
    resp = client_with_sqlite.post(
        "/analyses/9999/nl-filter",
        json={"query": "test"},
    )
    assert resp.status_code == 404


def test_nl_filter_endpoint_passes_query_to_service(client_with_sqlite, monkeypatch):
    import app.routes.analyses as analyses_mod

    captured: dict = {}

    class _CaptureLLM:
        def json_completion(self, *, system, user, max_tokens=512):
            captured["user"] = user
            return {"analyzer": None, "severity": None, "status": None, "search_text": None}

    monkeypatch.setattr(analyses_mod, "_nl_filter_llm", _CaptureLLM())

    from app.db import get_db
    db = next(client_with_sqlite.app.dependency_overrides[get_db]())
    aid = _seed_analysis(db)

    client_with_sqlite.post(
        f"/analyses/{aid}/nl-filter",
        json={"query": "labs in arm B"},
    )
    assert "labs in arm B" in captured.get("user", "")
