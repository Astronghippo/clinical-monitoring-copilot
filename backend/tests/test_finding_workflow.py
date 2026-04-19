"""Finding workflow: status, assignee, notes, bulk update."""
from unittest.mock import patch
from pathlib import Path
import json

from app.services.protocol_parser import ProtocolSpec

FIX = Path(__file__).parent / "fixtures"


def _fake_spec():
    return ProtocolSpec.model_validate(
        json.loads((FIX / "mini_protocol_spec.json").read_text())
    )


def _seed_one_finding(client):
    with patch("app.routes.protocols.parse_protocol_text", return_value=_fake_spec()), \
         patch("app.routes.protocols.extract_text_from_pdf_bytes", return_value="fake"):
        r = client.post("/protocols", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")})
        protocol_id = r.json()["id"]
    dm = (FIX / "mini_dataset" / "dm.csv").read_bytes()
    sv = (FIX / "mini_dataset" / "sv.csv").read_bytes()
    vs = (FIX / "mini_dataset" / "vs.csv").read_bytes()
    r = client.post("/datasets?name=mini", files=[
        ("files", ("dm.csv", dm, "text/csv")),
        ("files", ("sv.csv", sv, "text/csv")),
        ("files", ("vs.csv", vs, "text/csv")),
    ])
    dataset_id = r.json()["id"]
    with patch("app.services.analyzers.completeness.LLMClient") as MC, \
         patch("app.services.analyzers.eligibility.LLMClient") as ME:
        MC.return_value.json_completion.return_value = {
            "results": [{"subject_id": "1001", "visits": [
                {"visit_id": "V1", "missing": ["ECG"], "reasoning": "test"}
            ]}]
        }
        ME.return_value.json_completion.return_value = {"results": []}
        r = client.post("/analyses", json={"protocol_id": protocol_id, "dataset_id": dataset_id})
        analysis_id = r.json()["id"]
    r = client.get(f"/analyses/{analysis_id}")
    findings = r.json()["findings"]
    assert findings, "expected at least one seeded finding"
    return findings[0]["id"]


def test_patch_finding_status_updates_field(client_with_sqlite):
    fid = _seed_one_finding(client_with_sqlite)
    r = client_with_sqlite.get(f"/findings/{fid}")
    assert r.json()["status"] == "open"
    r = client_with_sqlite.patch(f"/findings/{fid}", json={"status": "in_review"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_review"
    r = client_with_sqlite.patch(
        f"/findings/{fid}",
        json={"assignee": "alex@example.com", "notes": "waiting on site response"},
    )
    assert r.json()["assignee"] == "alex@example.com"
    assert r.json()["notes"] == "waiting on site response"


def test_patch_finding_404_when_missing(client_with_sqlite):
    r = client_with_sqlite.patch("/findings/99999", json={"status": "resolved"})
    assert r.status_code == 404


def test_bulk_status_update_applies_to_all(client_with_sqlite):
    f1 = _seed_one_finding(client_with_sqlite)
    f2 = _seed_one_finding(client_with_sqlite)
    r = client_with_sqlite.post(
        "/findings/bulk-status",
        json={"finding_ids": [f1, f2], "status": "resolved"},
    )
    assert r.status_code == 200
    assert r.json() == {"updated": 2}
    assert client_with_sqlite.get(f"/findings/{f1}").json()["status"] == "resolved"
    assert client_with_sqlite.get(f"/findings/{f2}").json()["status"] == "resolved"
