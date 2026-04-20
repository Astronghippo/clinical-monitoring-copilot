"""Tests for PATCH /protocols/{id}/spec endpoint."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.services.protocol_parser import ProtocolSpec


FIX = Path(__file__).parent / "fixtures"


def _fake_spec_dict():
    return json.loads((FIX / "mini_protocol_spec.json").read_text())


def _create_protocol(client):
    """Helper: upload a protocol and return its id."""
    with patch("app.routes.protocols.parse_protocol_text") as mp, \
         patch("app.routes.protocols.extract_text_from_pdf_bytes", return_value="fake text"):
        mp.return_value = ProtocolSpec.model_validate(_fake_spec_dict())
        r = client.post(
            "/protocols",
            files={"file": ("test.pdf", b"%PDF-1.4\n", "application/pdf")},
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]


def test_patch_spec_valid(client_with_sqlite):
    """PATCH /protocols/{id}/spec with valid spec_json returns 200 and updated spec."""
    client = client_with_sqlite
    protocol_id = _create_protocol(client)

    new_spec = _fake_spec_dict()
    # Modify to confirm update took effect
    new_spec["visits"][0]["name"] = "Updated Baseline"
    new_spec["visits"][0]["nominal_day"] = 1

    r = client.patch(
        f"/protocols/{protocol_id}/spec",
        json={"spec_json": new_spec},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["spec_json"]["visits"][0]["name"] == "Updated Baseline"
    assert data["spec_json"]["visits"][0]["nominal_day"] == 1


def test_patch_spec_invalid_missing_field(client_with_sqlite):
    """PATCH /protocols/{id}/spec with invalid spec_json returns 422."""
    client = client_with_sqlite
    protocol_id = _create_protocol(client)

    # Missing required 'study_id'
    invalid_spec = {
        "visits": [],
        "eligibility": [],
    }

    r = client.patch(
        f"/protocols/{protocol_id}/spec",
        json={"spec_json": invalid_spec},
    )
    assert r.status_code == 422, r.text


def test_patch_spec_not_found(client_with_sqlite):
    """PATCH /protocols/{nonexistent}/spec returns 404."""
    client = client_with_sqlite

    r = client.patch(
        "/protocols/99999/spec",
        json={"spec_json": _fake_spec_dict()},
    )
    assert r.status_code == 404, r.text


def test_patch_spec_invalid_visit_structure(client_with_sqlite):
    """PATCH with a visit missing required fields returns 422."""
    client = client_with_sqlite
    protocol_id = _create_protocol(client)

    bad_spec = {
        "study_id": "TEST-001",
        "visits": [{"visit_id": "V1"}],  # missing name, nominal_day
        "eligibility": [],
    }

    r = client.patch(
        f"/protocols/{protocol_id}/spec",
        json={"spec_json": bad_spec},
    )
    assert r.status_code == 422, r.text


def test_patch_spec_rejected_during_parse(client_with_sqlite):
    """PATCH /protocols/{id}/spec returns 409 when parse_status is 'parsing'."""
    from app.db import SessionLocal
    from app.models import Protocol

    client = client_with_sqlite

    # Create a protocol directly with parse_status="parsing" to simulate an
    # in-progress parse.
    with patch("app.routes.protocols.extract_text_from_pdf_bytes", return_value="fake text"), \
         patch("app.routes.protocols._parse_in_background"):  # prevent background task from running
        r = client.post(
            "/protocols",
            files={"file": ("test.pdf", b"%PDF-1.4\n", "application/pdf")},
        )
        assert r.status_code == 200, r.text
        protocol_id = r.json()["id"]

    # The freshly uploaded protocol starts with parse_status="parsing".
    # Attempting a PATCH now should yield 409.
    r = client.patch(
        f"/protocols/{protocol_id}/spec",
        json={"spec_json": _fake_spec_dict()},
    )
    assert r.status_code == 409, r.text
    assert "parse" in r.json()["detail"].lower()


def test_patch_spec_syncs_study_id(client_with_sqlite):
    """PATCH /protocols/{id}/spec updates the top-level study_id on the Protocol row."""
    client = client_with_sqlite
    protocol_id = _create_protocol(client)

    new_spec = _fake_spec_dict()
    new_spec["study_id"] = "NEW-STUDY-999"

    r = client.patch(
        f"/protocols/{protocol_id}/spec",
        json={"spec_json": new_spec},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["study_id"] == "NEW-STUDY-999", (
        "top-level study_id must be synced from spec after PATCH"
    )
