from app.services.report_pdf import render_analysis_pdf
from app.models import Analysis, Protocol, FindingRow
from datetime import datetime


def test_pdf_renders_for_mixed_severities():
    p = Protocol(id=1, study_id="TEST", filename="x.pdf", raw_text="", spec_json={},
                 parse_status="done", created_at=datetime.utcnow())
    a = Analysis(id=1, protocol_id=1, dataset_id=1, status="done",
                 name=None, created_at=datetime.utcnow())
    a.findings = [
        FindingRow(id=1, analysis_id=1, analyzer="visit_windows", severity="critical",
                   subject_id="1001", summary="C1", detail="d", protocol_citation="\u00a76",
                   data_citation={}, confidence=1.0, status="open"),
        FindingRow(id=2, analysis_id=1, analyzer="completeness", severity="major",
                   subject_id="1002", summary="M1", detail="d", protocol_citation="\u00a77",
                   data_citation={}, confidence=0.85, status="open"),
    ]
    pdf = render_analysis_pdf(a, p)
    assert pdf.startswith(b"%PDF-"), "expected a valid PDF header"
    assert len(pdf) > 1000
