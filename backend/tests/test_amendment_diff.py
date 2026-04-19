"""Tests for POST /analyses/{analysis_id}/amendment-diff endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.services.protocol_parser import EligibilityCriterion, ProtocolSpec, VisitDef


# ---------------------------------------------------------------------------
# Helpers to build minimal DB state via the real API
# ---------------------------------------------------------------------------

def _upload_protocol(client: TestClient) -> int:
    """Upload a minimal protocol and return protocol_id. Bypasses background parse."""
    with (
        patch("app.routes.protocols.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.protocols._parse_in_background"),
    ):
        mock_extract.return_value = "protocol text"
        r = client.post(
            "/protocols",
            files={"file": ("proto.pdf", b"%PDF-fake", "application/pdf")},
        )
    assert r.status_code == 200
    protocol_id = r.json()["id"]

    # Directly set spec_json on the protocol row via admin endpoint or a patch.
    # We'll use the DB directly through the test session.
    return protocol_id


def _seed_analysis(client: TestClient, spec: ProtocolSpec) -> tuple[int, int]:
    """Create a protocol + dataset + analysis with the given spec_json.

    Returns (analysis_id, protocol_id).
    Uses the patched SessionLocal so writes go to the test DB.
    """
    from app.models import Analysis, Dataset, Protocol
    import app.routes.analyses as analyses_mod

    with (
        patch("app.routes.protocols.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.protocols._parse_in_background"),
    ):
        mock_extract.return_value = "protocol text"
        r = client.post(
            "/protocols",
            files={"file": ("proto.pdf", b"%PDF-fake", "application/pdf")},
        )
    assert r.status_code == 200, r.text
    protocol_id = r.json()["id"]

    # Use the patched SessionLocal (same DB the test client uses).
    db = analyses_mod.SessionLocal()
    try:
        p = db.get(Protocol, protocol_id)
        p.spec_json = spec.model_dump()
        p.parse_status = "done"
        db.commit()

        # Create a dummy dataset.
        dataset = Dataset(name="test-dataset", storage_path="/dev/null")
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        dataset_id = dataset.id

        # Create analysis.
        analysis = Analysis(
            protocol_id=protocol_id,
            dataset_id=dataset_id,
            status="done",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        analysis_id = analysis.id
    finally:
        db.close()

    return analysis_id, protocol_id


def _add_findings(analysis_id: int, findings_data: list[dict]) -> list[int]:
    """Add FindingRow records to an analysis and return their IDs."""
    from app.models import FindingRow
    import app.routes.analyses as analyses_mod

    db = analyses_mod.SessionLocal()
    try:
        ids = []
        for fd in findings_data:
            f = FindingRow(
                analysis_id=analysis_id,
                analyzer=fd.get("analyzer", "visit_windows"),
                severity=fd.get("severity", "major"),
                subject_id=fd.get("subject_id", "SUBJ001"),
                summary=fd.get("summary", "Test finding"),
                detail=fd.get("detail", ""),
                protocol_citation=fd.get("protocol_citation", ""),
                data_citation=fd.get("data_citation", {}),
                confidence=fd.get("confidence", 0.8),
            )
            db.add(f)
        db.commit()
        # Re-query to get IDs
        for f in (
            db.query(FindingRow)
            .filter(FindingRow.analysis_id == analysis_id)
            .all()
        ):
            ids.append(f.id)
        return ids
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ORIGINAL_SPEC = ProtocolSpec(
    study_id="STUDY-001",
    visits=[
        VisitDef(
            visit_id="V1",
            name="Screening",
            nominal_day=-14,
            window_minus_days=3,
            window_plus_days=3,
        ),
        VisitDef(
            visit_id="V2",
            name="Baseline",
            nominal_day=0,
            window_minus_days=1,
            window_plus_days=1,
        ),
        VisitDef(
            visit_id="V3",
            name="Week 4",
            nominal_day=28,
            window_minus_days=3,
            window_plus_days=3,
        ),
    ],
    eligibility=[
        EligibilityCriterion(
            criterion_id="I1",
            kind="inclusion",
            text="Age >= 18 years",
        ),
        EligibilityCriterion(
            criterion_id="I2",
            kind="inclusion",
            text="HbA1c between 7.5% and 10.5%",
        ),
    ],
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_amendment_diff_404_missing_analysis(client_with_sqlite):
    """Endpoint returns 404 when analysis does not exist."""
    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text"),
    ):
        mock_extract.return_value = "protocol text"
        r = client_with_sqlite.post(
            "/analyses/99999/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )
    assert r.status_code == 404


def test_amendment_diff_400_non_pdf(client_with_sqlite):
    """Endpoint returns 400 when uploaded file is not a PDF."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    r = client_with_sqlite.post(
        f"/analyses/{analysis_id}/amendment-diff",
        files={"file": ("not-a-pdf.txt", b"just text", "text/plain")},
    )
    assert r.status_code == 400


def test_amendment_diff_added_visits(client_with_sqlite):
    """added_visits contains visits in amended spec not in original."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    amended_spec = ProtocolSpec(
        study_id="STUDY-001",
        visits=ORIGINAL_SPEC.visits + [
            VisitDef(
                visit_id="V4",
                name="Week 8",
                nominal_day=56,
                window_minus_days=3,
                window_plus_days=3,
            )
        ],
        eligibility=ORIGINAL_SPEC.eligibility,
    )

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "amended protocol text"
        mock_parse.return_value = amended_spec

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert "Week 8" in data["added_visits"]
    assert data["removed_visits"] == []
    assert data["changed_visits"] == []


def test_amendment_diff_removed_visits(client_with_sqlite):
    """removed_visits contains visits in original but not amended."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    # Amended: remove "Week 4"
    amended_spec = ProtocolSpec(
        study_id="STUDY-001",
        visits=[v for v in ORIGINAL_SPEC.visits if v.name != "Week 4"],
        eligibility=ORIGINAL_SPEC.eligibility,
    )

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "amended protocol text"
        mock_parse.return_value = amended_spec

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert "Week 4" in data["removed_visits"]
    assert data["added_visits"] == []


def test_amendment_diff_changed_visits(client_with_sqlite):
    """changed_visits contains visits where window changed."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    # Amended: Baseline window changed from ±1 to ±3
    amended_visits = [
        VisitDef(
            visit_id="V1",
            name="Screening",
            nominal_day=-14,
            window_minus_days=3,
            window_plus_days=3,
        ),
        VisitDef(
            visit_id="V2",
            name="Baseline",
            nominal_day=0,
            window_minus_days=3,  # changed from 1
            window_plus_days=3,   # changed from 1
        ),
        VisitDef(
            visit_id="V3",
            name="Week 4",
            nominal_day=28,
            window_minus_days=3,
            window_plus_days=3,
        ),
    ]
    amended_spec = ProtocolSpec(
        study_id="STUDY-001",
        visits=amended_visits,
        eligibility=ORIGINAL_SPEC.eligibility,
    )

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "amended protocol text"
        mock_parse.return_value = amended_spec

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert "Baseline" in data["changed_visits"]
    assert data["removed_visits"] == []
    assert data["added_visits"] == []


def test_amendment_diff_obsolete_findings_visit_windows(client_with_sqlite):
    """obsolete_finding_ids includes visit_windows findings for removed visits."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    # Add findings: one for "Week 4" (will be removed), one for "Baseline"
    _add_findings(analysis_id, [
        {
            "analyzer": "visit_windows",
            "severity": "major",
            "subject_id": "SUBJ001",
            "summary": "Week 4 visit window violation",
            "detail": "Visit occurred outside allowed window",
            "protocol_citation": "Week 4 ±3 days",
            "data_citation": {"visit": "Week 4"},
            "confidence": 0.9,
        },
        {
            "analyzer": "visit_windows",
            "severity": "minor",
            "subject_id": "SUBJ002",
            "summary": "Baseline visit window violation",
            "detail": "Visit occurred outside allowed window",
            "protocol_citation": "Baseline ±1 days",
            "data_citation": {"visit": "Baseline"},
            "confidence": 0.9,
        },
    ])

    # Re-fetch finding IDs
    from app.models import FindingRow
    import app.routes.analyses as analyses_mod
    db = analyses_mod.SessionLocal()
    try:
        findings = db.query(FindingRow).filter(FindingRow.analysis_id == analysis_id).all()
        week4_finding_id = next(f.id for f in findings if "Week 4" in f.protocol_citation)
        baseline_finding_id = next(f.id for f in findings if "Baseline" in f.protocol_citation)
    finally:
        db.close()

    # Amended: remove "Week 4"
    amended_spec = ProtocolSpec(
        study_id="STUDY-001",
        visits=[v for v in ORIGINAL_SPEC.visits if v.name != "Week 4"],
        eligibility=ORIGINAL_SPEC.eligibility,
    )

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "amended protocol text"
        mock_parse.return_value = amended_spec

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert week4_finding_id in data["obsolete_finding_ids"]
    assert baseline_finding_id not in data["obsolete_finding_ids"]


def test_amendment_diff_obsolete_findings_eligibility(client_with_sqlite):
    """obsolete_finding_ids includes eligibility findings for removed criteria."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    _add_findings(analysis_id, [
        {
            "analyzer": "eligibility",
            "severity": "critical",
            "subject_id": "SUBJ001",
            "summary": "HbA1c outside range",
            "detail": "Subject HbA1c between 7.5% and 10.5% criterion not met",
            "protocol_citation": "HbA1c between 7.5% and 10.5%",
            "data_citation": {},
            "confidence": 0.95,
        },
        {
            "analyzer": "eligibility",
            "severity": "critical",
            "subject_id": "SUBJ002",
            "summary": "Age criterion violation",
            "detail": "Subject does not meet Age >= 18 years requirement",
            "protocol_citation": "Age >= 18 years",
            "data_citation": {},
            "confidence": 0.95,
        },
    ])

    from app.models import FindingRow
    import app.routes.analyses as analyses_mod
    db = analyses_mod.SessionLocal()
    try:
        findings = db.query(FindingRow).filter(FindingRow.analysis_id == analysis_id).all()
        hba1c_id = next(f.id for f in findings if "HbA1c" in f.detail)
        age_id = next(f.id for f in findings if "Age" in f.detail)
    finally:
        db.close()

    # Amended: remove HbA1c criterion
    amended_spec = ProtocolSpec(
        study_id="STUDY-001",
        visits=ORIGINAL_SPEC.visits,
        eligibility=[c for c in ORIGINAL_SPEC.eligibility if "HbA1c" not in c.text],
    )

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "amended protocol text"
        mock_parse.return_value = amended_spec

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert hba1c_id in data["obsolete_finding_ids"]
    assert age_id not in data["obsolete_finding_ids"]


def test_amendment_diff_no_changes(client_with_sqlite):
    """Returns empty lists when amended spec matches original."""
    analysis_id, _ = _seed_analysis(client_with_sqlite, ORIGINAL_SPEC)

    with (
        patch("app.routes.analyses.extract_text_from_pdf_bytes") as mock_extract,
        patch("app.routes.analyses.parse_protocol_text") as mock_parse,
    ):
        mock_extract.return_value = "protocol text"
        mock_parse.return_value = ORIGINAL_SPEC  # identical

        r = client_with_sqlite.post(
            f"/analyses/{analysis_id}/amendment-diff",
            files={"file": ("amendment.pdf", b"%PDF-fake", "application/pdf")},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["added_visits"] == []
    assert data["removed_visits"] == []
    assert data["changed_visits"] == []
    assert data["added_criteria"] == []
    assert data["removed_criteria"] == []
    assert data["obsolete_finding_ids"] == []
