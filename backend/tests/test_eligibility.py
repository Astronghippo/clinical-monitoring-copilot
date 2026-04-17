import pandas as pd

from app.services.analyzers.eligibility import EligibilityAnalyzer
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import EligibilityCriterion, ProtocolSpec


def _spec():
    return ProtocolSpec(
        study_id="T1", visits=[],
        eligibility=[
            EligibilityCriterion(criterion_id="I1", kind="inclusion",
                                 text="Adults 18-75 with type 2 diabetes."),
            EligibilityCriterion(criterion_id="I2", kind="inclusion",
                                 text="HbA1c between 7.0% and 10.5% at screening."),
            EligibilityCriterion(criterion_id="E2", kind="exclusion",
                                 text="HbA1c > 10.5% at screening."),
        ],
    )


def _ds(dm_rows):
    dm = pd.DataFrame(dm_rows)
    sv = pd.DataFrame(columns=["USUBJID", "VISIT", "VISITNUM", "SVSTDTC"])
    vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    return PatientDataset(dm=dm, sv=sv, vs=vs)


class StubLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def json_completion(self, *, system, user, max_tokens=4096):
        self.calls.append({"system": system, "user": user})
        return self._responses.pop(0)


def test_no_findings_for_compliant_subject():
    dm = [{"USUBJID": "1001", "AGE": 55, "SEX": "M", "HBA1C_SCREEN": 8.1}]
    llm = StubLLM([{"results": [{"subject_id": "1001", "violations": []}]}])
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert findings == []


def test_flags_exclusion_violation():
    dm = [{"USUBJID": "1012", "AGE": 48, "SEX": "M", "HBA1C_SCREEN": 11.2}]
    llm = StubLLM([{
        "results": [{
            "subject_id": "1012",
            "violations": [{
                "criterion_id": "E2", "kind": "exclusion", "severity": "critical",
                "reason": "HbA1c 11.2% exceeds exclusion cutoff 10.5%",
            }],
        }]
    }])
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert len(findings) == 1
    f = findings[0]
    assert f.analyzer == "eligibility"
    assert f.subject_id == "1012"
    assert f.severity == "critical"
    assert "E2" in f.protocol_citation
    assert "11.2" in f.detail


def test_handles_nan_in_demographics_without_crashing():
    """pandas reads empty CSV cells as NaN (float); analyzer must normalize them to None."""
    dm = [{"USUBJID": "1001", "AGE": 55, "SEX": "M", "HBA1C_SCREEN": float("nan")}]
    llm = StubLLM([{"results": [{"subject_id": "1001", "violations": []}]}])
    # Should not raise
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert findings == []


def test_invalid_severity_defaults_to_major():
    dm = [{"USUBJID": "1012", "AGE": 48, "SEX": "M", "HBA1C_SCREEN": 11.2}]
    llm = StubLLM([{
        "results": [{
            "subject_id": "1012",
            "violations": [{
                "criterion_id": "E2", "kind": "exclusion", "severity": "WHATEVER",
                "reason": "unknown severity",
            }],
        }]
    }])
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert findings[0].severity == "major"


def test_no_criteria_returns_no_findings():
    spec_empty = ProtocolSpec(study_id="T1", visits=[], eligibility=[])
    dm = [{"USUBJID": "1001", "AGE": 55, "SEX": "M", "HBA1C_SCREEN": 8.1}]
    llm = StubLLM([])  # Should never be called
    findings = EligibilityAnalyzer(llm=llm).run(spec=spec_empty, dataset=_ds(dm))
    assert findings == []


def test_batches_all_subjects_into_single_call_when_under_batch_size():
    """3 subjects should fit in one batched LLM call (batch size is 20)."""
    dm = [
        {"USUBJID": "1001", "AGE": 55, "SEX": "M", "HBA1C_SCREEN": 8.1},
        {"USUBJID": "1002", "AGE": 62, "SEX": "F", "HBA1C_SCREEN": 9.0},
        {"USUBJID": "1012", "AGE": 48, "SEX": "M", "HBA1C_SCREEN": 11.2},
    ]
    llm = StubLLM([{
        "results": [
            {"subject_id": "1001", "violations": []},
            {"subject_id": "1002", "violations": []},
            {"subject_id": "1012", "violations": [{
                "criterion_id": "E2", "kind": "exclusion", "severity": "critical",
                "reason": "HbA1c 11.2% exceeds cutoff",
            }]},
        ]
    }])
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert len(llm.calls) == 1  # One batched call, not three
    assert len(findings) == 1
    assert findings[0].subject_id == "1012"


def test_chunks_when_over_batch_size():
    """45 subjects should chunk into ceil(45/20) = 3 LLM calls."""
    dm = [
        {"USUBJID": f"{1000 + i}", "AGE": 55, "SEX": "M", "HBA1C_SCREEN": 8.0}
        for i in range(45)
    ]
    # Each batch returns empty violations for its 20/20/5 subjects.
    responses = [
        {"results": [{"subject_id": f"{1000 + i}", "violations": []} for i in range(0, 20)]},
        {"results": [{"subject_id": f"{1000 + i}", "violations": []} for i in range(20, 40)]},
        {"results": [{"subject_id": f"{1000 + i}", "violations": []} for i in range(40, 45)]},
    ]
    llm = StubLLM(responses)
    findings = EligibilityAnalyzer(llm=llm).run(spec=_spec(), dataset=_ds(dm))
    assert len(llm.calls) == 3
    assert findings == []
