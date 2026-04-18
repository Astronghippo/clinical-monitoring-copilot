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


def _single_subject_response(subject_id, visits):
    """Helper: wrap per-subject data in the new multi-subject batch shape."""
    return {"results": [{"subject_id": subject_id, "visits": visits}]}


def test_no_findings_when_all_captured():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        ("1001", "Baseline", "ECGINT", 400, "2025-06-01"),
    ]
    llm = StubLLM([_single_subject_response(
        "1001", [{"visit_id": "V1", "missing": [], "reasoning": "all present"}]
    )])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert findings == []


def test_flags_missing_procedure():
    vs = [
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Baseline", "HBA1C", 8.1, "2025-06-01"),
        # Missing ECG
    ]
    llm = StubLLM([_single_subject_response(
        "1001", [{"visit_id": "V1", "missing": ["ECG"], "reasoning": "no ECG"}]
    )])
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
    llm = StubLLM([_single_subject_response(
        "1001", [{"visit_id": "V1", "missing": ["Labs", "ECG"], "reasoning": "two missing"}]
    )])
    findings = CompletenessAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(vs))
    assert len(findings) == 2
    assert {f.summary.split(": ")[-1] for f in findings} == {"Labs", "ECG"}


def test_batches_multiple_subjects_into_a_single_call():
    """20 subjects should be sent in one batched LLM call, not 20 calls."""
    spec = ProtocolSpec(
        study_id="T1",
        visits=[VisitDef(visit_id="V1", name="Baseline", nominal_day=0,
                         required_procedures=["Vitals"])],
        eligibility=[],
    )
    # Build 15 subjects (under batch size 20 → 1 call).
    subjects = [f"100{i:02d}" for i in range(15)]
    dm = pd.DataFrame([{"USUBJID": sid, "RFSTDTC": "2025-06-01"} for sid in subjects])
    sv = pd.DataFrame([{
        "USUBJID": sid, "VISIT": "Baseline",
        "VISITNUM": 1, "SVSTDTC": "2025-06-01",
    } for sid in subjects])
    vs = pd.DataFrame([
        (sid, "Baseline", "SYSBP", 120, "2025-06-01") for sid in subjects
    ], columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ds = PatientDataset(dm=dm, sv=sv, vs=vs)

    # One canned response with all subjects, each visit = no missing.
    llm = StubLLM([{
        "results": [
            {"subject_id": sid, "visits": [
                {"visit_id": "V1", "missing": [], "reasoning": "ok"}
            ]} for sid in subjects
        ]
    }])
    findings = CompletenessAnalyzer(llm=llm).run(spec=spec, dataset=ds)
    assert len(llm.calls) == 1  # 15 subjects fit in one batch
    assert findings == []


def test_chunks_when_subjects_exceed_batch_size():
    """45 subjects → ceil(45/20) = 3 batched LLM calls."""
    spec = ProtocolSpec(
        study_id="T1",
        visits=[VisitDef(visit_id="V1", name="Baseline", nominal_day=0,
                         required_procedures=["Vitals"])],
        eligibility=[],
    )
    subjects = [f"{1000 + i}" for i in range(45)]
    dm = pd.DataFrame([{"USUBJID": sid, "RFSTDTC": "2025-06-01"} for sid in subjects])
    sv = pd.DataFrame([{
        "USUBJID": sid, "VISIT": "Baseline",
        "VISITNUM": 1, "SVSTDTC": "2025-06-01",
    } for sid in subjects])
    vs = pd.DataFrame([
        (sid, "Baseline", "SYSBP", 120, "2025-06-01") for sid in subjects
    ], columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ds = PatientDataset(dm=dm, sv=sv, vs=vs)

    # Three responses, one per batch.
    responses = []
    for batch_start in (0, 20, 40):
        batch_subjects = subjects[batch_start : batch_start + 20]
        responses.append({
            "results": [
                {"subject_id": sid, "visits": [
                    {"visit_id": "V1", "missing": [], "reasoning": "ok"}
                ]} for sid in batch_subjects
            ]
        })
    llm = StubLLM(responses)
    CompletenessAnalyzer(llm=llm).run(spec=spec, dataset=ds)
    assert len(llm.calls) == 3  # 45 / 20 = 3 batches


def test_per_subject_multiple_visits_still_bundled():
    """Within a batch, each subject can still have multiple visits."""
    spec = ProtocolSpec(
        study_id="T1",
        visits=[
            VisitDef(visit_id="V1", name="Baseline", nominal_day=0,
                     required_procedures=["Vitals"]),
            VisitDef(visit_id="V2", name="Week 2", nominal_day=14,
                     required_procedures=["Vitals", "Labs"]),
        ],
        eligibility=[],
    )
    dm = pd.DataFrame([{"USUBJID": "1001", "RFSTDTC": "2025-06-01"}])
    sv = pd.DataFrame([
        {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Week 2",   "VISITNUM": 2, "SVSTDTC": "2025-06-15"},
    ])
    vs = pd.DataFrame([
        ("1001", "Baseline", "SYSBP", 120, "2025-06-01"),
        ("1001", "Week 2",   "SYSBP", 118, "2025-06-15"),
    ], columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ds = PatientDataset(dm=dm, sv=sv, vs=vs)

    llm = StubLLM([{
        "results": [{
            "subject_id": "1001",
            "visits": [
                {"visit_id": "V1", "missing": [], "reasoning": "ok"},
                {"visit_id": "V2", "missing": ["Labs"], "reasoning": "no lab captured"},
            ],
        }]
    }])
    findings = CompletenessAnalyzer(llm=llm).run(spec=spec, dataset=ds)
    assert len(llm.calls) == 1
    assert len(findings) == 1
    assert "Labs" in findings[0].summary
