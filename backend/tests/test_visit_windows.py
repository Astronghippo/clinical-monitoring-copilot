import pandas as pd

from app.services.analyzers.base import Finding
from app.services.analyzers.visit_windows import VisitWindowAnalyzer
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec, VisitDef


def _spec():
    return ProtocolSpec(
        study_id="T1",
        visits=[
            VisitDef(visit_id="V1", name="Baseline", nominal_day=0,
                     window_minus_days=0, window_plus_days=0, required_procedures=[]),
            VisitDef(visit_id="V2", name="Week 2", nominal_day=14,
                     window_minus_days=2, window_plus_days=2, required_procedures=[]),
            VisitDef(visit_id="V3", name="Week 4", nominal_day=28,
                     window_minus_days=3, window_plus_days=3, required_procedures=[]),
        ],
        eligibility=[],
    )


def _ds(rows):
    dm = pd.DataFrame([{"USUBJID": "1001", "RFSTDTC": "2025-06-01"}])
    sv = pd.DataFrame(rows)
    vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    return PatientDataset(dm=dm, sv=sv, vs=vs)


def test_no_findings_when_all_in_window():
    rows = [
        {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Week 2",   "VISITNUM": 2, "SVSTDTC": "2025-06-15"},  # +1
        {"USUBJID": "1001", "VISIT": "Week 4",   "VISITNUM": 3, "SVSTDTC": "2025-06-30"},  # +1
    ]
    findings = VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(rows))
    assert findings == []


def test_flags_late_visit():
    rows = [
        {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Week 2",   "VISITNUM": 2, "SVSTDTC": "2025-06-15"},
        {"USUBJID": "1001", "VISIT": "Week 4",   "VISITNUM": 3, "SVSTDTC": "2025-07-04"},  # +5
    ]
    findings = VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(rows))
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, Finding)
    assert f.analyzer == "visit_windows"
    assert f.subject_id == "1001"
    assert "late" in f.summary.lower()
    assert f.confidence == 1.0


def test_flags_early_visit():
    rows = [
        {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Week 4",   "VISITNUM": 3, "SVSTDTC": "2025-06-20"},  # -8
    ]
    findings = VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(rows))
    assert len(findings) == 1
    assert "early" in findings[0].summary.lower()


def test_severity_scales_with_magnitude():
    # 1 day over (minor), 4 days over (major), 10 days over (critical)
    def make(days_over):
        return [
            {"USUBJID": "1001", "VISIT": "Baseline", "VISITNUM": 1, "SVSTDTC": "2025-06-01"},
            {"USUBJID": "1001", "VISIT": "Week 4", "VISITNUM": 3,
             # window +3, so actual = 28 + 3 + days_over
             "SVSTDTC": (pd.Timestamp("2025-06-01") + pd.Timedelta(days=28 + 3 + days_over)).date().isoformat()},
        ]

    assert VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(make(1)))[0].severity == "minor"
    assert VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(make(4)))[0].severity == "major"
    assert VisitWindowAnalyzer().run(spec=_spec(), dataset=_ds(make(10)))[0].severity == "critical"
