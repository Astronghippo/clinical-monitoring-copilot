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
    """Records each prompt sent and returns canned responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def json_completion(self, *, system, user, max_tokens=4096):
        self.calls.append({"system": system, "user": user})
        return self._responses.pop(0)


def test_no_findings_when_all_captured():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        ("1001", "Baseline", "ECGINT", 400, "2025-06-01"),
    ]
    # Batched response: one entry per visit.
    llm = StubLLM([{"visits": [{"visit_id": "V1", "missing": [], "reasoning": "all present"}]}])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert findings == []


def test_flags_missing_procedure():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        # Missing ECG
    ]
    llm = StubLLM([{
        "visits": [
            {"visit_id": "V1", "missing": ["ECG"], "reasoning": "no ECG testcode captured"}
        ]
    }])
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
    llm = StubLLM([{
        "visits": [
            {"visit_id": "V1", "missing": ["Labs", "ECG"], "reasoning": "missing both"}
        ]
    }])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert len(findings) == 2
    assert {f.summary.split(": ")[-1] for f in findings} == {"Labs", "ECG"}


def test_batches_one_call_per_subject_across_multiple_visits():
    """Single LLM call for a subject with many visits (was one per visit before)."""
    spec = ProtocolSpec(
        study_id="T1",
        visits=[
            VisitDef(visit_id="V1", name="Baseline", nominal_day=0,
                     required_procedures=["Vitals"]),
            VisitDef(visit_id="V2", name="Week 2", nominal_day=14,
                     required_procedures=["Vitals", "Labs"]),
            VisitDef(visit_id="V3", name="Week 4", nominal_day=28,
                     required_procedures=["Vitals", "Labs", "ECG"]),
        ],
        eligibility=[],
    )
    dm = pd.DataFrame([{"USUBJID": "1001", "RFSTDTC": "2025-06-01"}])
    sv = pd.DataFrame([
        {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Week 2",   "VISITNUM": 2, "SVSTDTC": "2025-06-15"},
        {"USUBJID": "1001", "VISIT": "Week 4",   "VISITNUM": 3, "SVSTDTC": "2025-06-29"},
    ])
    vs = pd.DataFrame([
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Week 2",   "SYSBP", 118, "2025-06-15"),  # missing Labs
        ("1001", "Week 4",   "SYSBP", 122, "2025-06-29"),  # missing Labs + ECG
    ], columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ds = PatientDataset(dm=dm, sv=sv, vs=vs)

    llm = StubLLM([{
        "visits": [
            {"visit_id": "V1", "missing": [], "reasoning": "ok"},
            {"visit_id": "V2", "missing": ["Labs"], "reasoning": "no lab captured"},
            {"visit_id": "V3", "missing": ["Labs", "ECG"], "reasoning": "two missing"},
        ]
    }])
    findings = CompletenessAnalyzer(llm=llm).run(spec=spec, dataset=ds)
    # One LLM call total (batched across the subject's visits).
    assert len(llm.calls) == 1
    # V2 → 1 missing; V3 → 2 missing; V1 → 0 missing. Total 3 findings.
    assert len(findings) == 3
