"""Tests for PlausibilityAnalyzer (TDD — written before implementation)."""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.analyzers.base import Finding
from app.services.analyzers.plausibility import PlausibilityAnalyzer
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec, VisitDef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spec() -> ProtocolSpec:
    """Minimal ProtocolSpec — plausibility analyzer doesn't use it but needs one."""
    return ProtocolSpec(
        study_id="PLAUS01",
        visits=[
            VisitDef(
                visit_id="V1",
                name="Baseline",
                nominal_day=0,
                window_minus_days=0,
                window_plus_days=0,
                required_procedures=[],
            )
        ],
        eligibility=[],
    )


def _ds(vs_rows: list[dict]) -> PatientDataset:
    """Build a minimal PatientDataset with only the VS rows provided."""
    dm = pd.DataFrame([{"USUBJID": "1001", "RFSTDTC": "2025-06-01"}])
    sv = pd.DataFrame(columns=["USUBJID", "VISIT", "VISITNUM", "SVSTDTC"])
    vs = pd.DataFrame(vs_rows) if vs_rows else pd.DataFrame(
        columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"]
    )
    return PatientDataset(dm=dm, sv=sv, vs=vs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sysbp_implausible_high():
    """SYSBP = 350 mmHg is outside the 50-300 plausible range → should be flagged."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "350", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, Finding)
    assert f.analyzer == "plausibility"
    assert f.subject_id == "1001"
    assert "SYSBP" in f.summary
    assert f.confidence == 1.0


def test_hba1c_negative():
    """HbA1c = -2 is negative and outside 2-20 range → flagged as implausible."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "HBA1C", "VSORRES": "-2", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    f = findings[0]
    assert f.analyzer == "plausibility"
    assert "HBA1C" in f.summary


def test_value_within_range_no_finding():
    """SYSBP = 120 is within 50-300 → no finding."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "120", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert findings == []


def test_non_numeric_vsorres_skipped():
    """Non-numeric VSORRES (e.g. 'N/A', 'PENDING') → no crash, no finding."""
    ds = _ds([
        {"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "N/A", "VSDTC": "2025-06-01"},
        {"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "HR", "VSORRES": "PENDING", "VSDTC": "2025-06-01"},
    ])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert findings == []


def test_severity_critical_far_outside():
    """HR = 500 bpm is > 20% of range (280) outside the 20-300 range → critical."""
    # Range width = 300-20 = 280; 20% = 56; 500 is 200 above max → > 20% → critical
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "HR", "VSORRES": "500", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    assert findings[0].severity == "critical"


def test_severity_major_close_outside():
    """SYSBP = 306 is just outside 50-300 by 6 mmHg.

    Range width = 250; 20% = 50; 6 < 50 → major.
    """
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "306", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    assert findings[0].severity == "major"


def test_severity_minor_zero_when_min_positive():
    """SYSBP = 0 when min > 0 → minor (could be missing data)."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "0", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    assert findings[0].severity == "minor"


def test_unknown_testcd_no_finding():
    """A VSTESTCD not in the rules table → no finding (ignore unknown tests)."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "UNKNOWN_LAB", "VSORRES": "99999", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert findings == []


def test_multiple_subjects_multiple_findings():
    """Multiple subjects, some with issues, some without."""
    dm = pd.DataFrame([
        {"USUBJID": "1001", "RFSTDTC": "2025-06-01"},
        {"USUBJID": "1002", "RFSTDTC": "2025-06-01"},
    ])
    sv = pd.DataFrame(columns=["USUBJID", "VISIT", "VISITNUM", "SVSTDTC"])
    vs = pd.DataFrame([
        {"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "SYSBP", "VSORRES": "120", "VSDTC": "2025-06-01"},
        {"USUBJID": "1002", "VISIT": "Baseline", "VSTESTCD": "TEMP", "VSORRES": "200", "VSDTC": "2025-06-01"},
    ])
    ds = PatientDataset(dm=dm, sv=sv, vs=vs)
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    assert findings[0].subject_id == "1002"
    assert "TEMP" in findings[0].summary


def test_empty_vs_no_crash():
    """Empty VS domain → no findings, no crash."""
    ds = _ds([])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert findings == []


def test_pulse_alias_recognized():
    """PULSE is an alias for HR/HEARTRT — should be checked against HR rule."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "PULSE", "VSORRES": "350", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1


def test_gluc_alias_recognized():
    """GLUCOSE is an alias for GLUC — should be checked against glucose rule."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "GLUCOSE", "VSORRES": "100", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1


def test_finding_data_citation_contains_domain():
    """data_citation should identify the VS domain and relevant row info."""
    ds = _ds([{"USUBJID": "1001", "VISIT": "Baseline", "VSTESTCD": "BMI", "VSORRES": "0", "VSDTC": "2025-06-01"}])
    findings = PlausibilityAnalyzer().run(spec=_spec(), dataset=ds)
    assert len(findings) == 1
    assert findings[0].data_citation.get("domain") == "VS"
    assert findings[0].data_citation.get("usubjid") == "1001"
