import pandas as pd

from app.services.analyzers.completeness import (
    DEFAULT_TESTCODE_MAP,
    CompletenessAnalyzer,
)
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec, VisitDef


def _spec():
    return ProtocolSpec(
        study_id="T1",
        visits=[
            VisitDef(
                visit_id="V1", name="Baseline", nominal_day=0,
                required_procedures=["Vitals", "Labs", "ECG"],
            ),
        ],
        eligibility=[],
    )


def _ds(vs_rows):
    dm = pd.DataFrame([{"USUBJID": "1001", "RFSTDTC": "2025-06-01"}])
    sv = pd.DataFrame([{
        "USUBJID": "1001", "VISIT": "Baseline",
        "VISITNUM": 1, "SVSTDTC": "2025-06-01",
    }])
    vs = pd.DataFrame(
        vs_rows, columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"],
    )
    return PatientDataset(dm=dm, sv=sv, vs=vs)


class StubLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def json_completion(self, *, system, user, max_tokens=4096):
        return self._responses.pop(0)


def test_no_findings_when_all_captured():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        ("1001", "Baseline", "ECGINT", 400, "2025-06-01"),
    ]
    llm = StubLLM([{"missing": [], "reasoning": "all present"}])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert findings == []


def test_flags_missing_procedure():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        # Missing ECG
    ]
    llm = StubLLM([{"missing": ["ECG"], "reasoning": "no ECG testcode captured"}])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert len(findings) == 1
    f = findings[0]
    assert f.analyzer == "completeness"
    assert "ECG" in f.summary
    assert f.subject_id == "1001"


def test_default_testcode_map_includes_common_codes():
    assert DEFAULT_TESTCODE_MAP["SYSBP"] == "Vitals"
    assert DEFAULT_TESTCODE_MAP["HBA1C"] == "Labs"
    assert DEFAULT_TESTCODE_MAP["ECGINT"] == "ECG"


def test_multiple_missing_produces_multiple_findings():
    vs = [("1001", "Baseline", "SYSBP", 120, "2025-06-01")]
    llm = StubLLM([{"missing": ["Labs", "ECG"], "reasoning": "missing both"}])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert len(findings) == 2
    assert {f.summary.split(": ")[-1] for f in findings} == {"Labs", "ECG"}
