"""Grouped findings endpoint: collapses near-duplicate findings by template."""
from unittest.mock import patch
from pathlib import Path
import json
import time

from app.services.protocol_parser import ProtocolSpec

FIX = Path(__file__).parent / "fixtures"

def _fake_spec():
    return ProtocolSpec.model_validate(json.loads((FIX / "mini_protocol_spec.json").read_text()))


def test_grouped_findings_collapses_duplicates(client_with_sqlite):
    with patch("app.routes.protocols.parse_protocol_text", return_value=_fake_spec()), \
         patch("app.routes.protocols.extract_text_from_pdf_bytes", return_value="fake"):
        r = client_with_sqlite.post("/protocols", files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")})
        pid = r.json()["id"]
    # Create dataset with 3 subjects, all with Baseline visit
    dm = b"USUBJID,SITEID,AGE,SEX,RACE,HBA1C_SCREEN,RFSTDTC\n1001,SITE01,55,M,WHITE,8.1,2025-06-01\n1002,SITE01,62,F,WHITE,9.4,2025-06-03\n1003,SITE01,48,M,WHITE,11.2,2025-06-05\n"
    sv = b"USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,2025-06-01\n1002,Baseline,1,2025-06-03\n1003,Baseline,1,2025-06-05\n"
    vs = b"USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,2025-06-01\n1001,Baseline,HBA1C,8.1,2025-06-01\n1002,Baseline,SYSBP,125,2025-06-03\n1002,Baseline,HBA1C,9.4,2025-06-03\n1003,Baseline,SYSBP,132,2025-06-05\n1003,Baseline,HBA1C,11.2,2025-06-05\n"
    r = client_with_sqlite.post("/datasets?name=g", files=[
        ("files", ("dm.csv", dm, "text/csv")),
        ("files", ("sv.csv", sv, "text/csv")),
        ("files", ("vs.csv", vs, "text/csv")),
    ])
    did = r.json()["id"]
    with patch("app.services.analyzers.completeness.LLMClient") as MC, \
         patch("app.services.analyzers.eligibility.LLMClient") as ME:
        MC.return_value.json_completion.return_value = {
            "results": [
                {"subject_id": "1001", "visits": [{"visit_id": "V1", "missing": ["ECG"], "reasoning": "x"}]},
                {"subject_id": "1002", "visits": [{"visit_id": "V1", "missing": ["ECG"], "reasoning": "x"}]},
                {"subject_id": "1003", "visits": [{"visit_id": "V1", "missing": ["ECG"], "reasoning": "x"}]},
            ]
        }
        ME.return_value.json_completion.return_value = {"results": []}
        r = client_with_sqlite.post("/analyses", json={"protocol_id": pid, "dataset_id": did})
        aid = r.json()["id"]

    # Wait for analysis to complete and findings to be stored
    for _ in range(10):
        r = client_with_sqlite.get(f"/analyses/{aid}")
        if r.json()["status"] == "done":
            break
        time.sleep(0.1)

    r = client_with_sqlite.get(f"/analyses/{aid}/grouped")
    assert r.status_code == 200
    groups = r.json()
    matched = [g for g in groups if "missing" in g["template"].lower() and g["count"] == 3]
    assert matched, f"expected a group of 3, got {groups}"
    assert len(matched[0]["subject_ids"]) == 3
