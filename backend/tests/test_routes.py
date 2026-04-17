"""End-to-end integration test for the three API routers.

Uses a file-based SQLite database + dependency override so tests don't need Postgres.
Patches the LLM parser and analyzer LLM clients so no API calls are made.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.services.protocol_parser import ProtocolSpec


FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def client_with_sqlite():
    # Use a temporary file-based SQLite database instead of in-memory
    # to ensure the connection persists across thread boundaries in TestClient
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(engine)

        def _override_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        # Patch SessionLocal used by the background task too
        import app.routes.analyses as analyses_mod
        original_session_local = analyses_mod.SessionLocal
        analyses_mod.SessionLocal = TestSession
        app.dependency_overrides[get_db] = _override_db

        client = TestClient(app)
        try:
            yield client
        finally:
            analyses_mod.SessionLocal = original_session_local
            app.dependency_overrides.clear()
    finally:
        import os
        os.close(db_fd)
        Path(db_path).unlink(missing_ok=True)


def _fake_spec_dict():
    return json.loads((FIX / "mini_protocol_spec.json").read_text())


def test_full_flow_smoke(client_with_sqlite):
    client = client_with_sqlite

    # 1) Upload protocol (patch parser + pdf extractor)
    with patch("app.routes.protocols.parse_protocol_text") as mp, \
         patch("app.routes.protocols.extract_text_from_pdf_bytes", return_value="fake"):
        mp.return_value = ProtocolSpec.model_validate(_fake_spec_dict())
        r = client.post(
            "/protocols",
            files={"file": ("x.pdf", b"%PDF-1.4\n", "application/pdf")},
        )
        assert r.status_code == 200, r.text
        protocol_id = r.json()["id"]

    # 2) Upload dataset (CSV fixtures)
    dm = (FIX / "mini_dataset" / "dm.csv").read_bytes()
    sv = (FIX / "mini_dataset" / "sv.csv").read_bytes()
    vs = (FIX / "mini_dataset" / "vs.csv").read_bytes()
    r = client.post(
        "/datasets?name=mini",
        files=[
            ("files", ("dm.csv", dm, "text/csv")),
            ("files", ("sv.csv", sv, "text/csv")),
            ("files", ("vs.csv", vs, "text/csv")),
        ],
    )
    assert r.status_code == 200, r.text
    dataset_id = r.json()["id"]

    # 3) Trigger analysis (stub the LLM-using analyzers)
    with patch("app.services.analyzers.completeness.LLMClient") as MC, \
         patch("app.services.analyzers.eligibility.LLMClient") as ME:
        MC.return_value.json_completion.return_value = {"missing": [], "reasoning": "ok"}
        ME.return_value.json_completion.return_value = {"violations": []}
        r = client.post(
            "/analyses",
            json={"protocol_id": protocol_id, "dataset_id": dataset_id},
        )
        assert r.status_code == 200, r.text
        analysis_id = r.json()["id"]

        # 4) Poll for result — background task runs synchronously in TestClient
        for _ in range(20):
            r = client.get(f"/analyses/{analysis_id}")
            if r.json()["status"] in ("done", "error"):
                break
        assert r.json()["status"] == "done", r.json()


def test_upload_non_pdf_rejected(client_with_sqlite):
    r = client_with_sqlite.post(
        "/protocols",
        files={"file": ("x.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_create_analysis_404_when_protocol_missing(client_with_sqlite):
    r = client_with_sqlite.post(
        "/analyses",
        json={"protocol_id": 999, "dataset_id": 999},
    )
    assert r.status_code == 404
