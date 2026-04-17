from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Analysis, Dataset, FindingRow, Protocol


def _inmem_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_model_roundtrip():
    db = _inmem_session()
    try:
        p = Protocol(study_id="TEST-001", filename="x.pdf", raw_text="hi", spec_json={})
        d = Dataset(name="mini", storage_path="/tmp")
        db.add_all([p, d])
        db.flush()
        a = Analysis(protocol_id=p.id, dataset_id=d.id, status="done")
        db.add(a)
        db.flush()
        f = FindingRow(
            analysis_id=a.id,
            analyzer="visit_windows",
            severity="major",
            subject_id="1001",
            summary="x",
            detail="y",
            protocol_citation="§6",
            data_citation={"row": 1},
            confidence=0.9,
        )
        db.add(f)
        db.commit()
        got = db.get(Analysis, a.id)
        assert got is not None
        assert len(got.findings) == 1
        assert got.findings[0].analyzer == "visit_windows"
    finally:
        db.rollback()
        db.close()


def test_cascade_delete_findings():
    db = _inmem_session()
    try:
        p = Protocol(study_id="T2", filename="x.pdf", raw_text="", spec_json={})
        d = Dataset(name="x", storage_path="/tmp")
        db.add_all([p, d])
        db.flush()
        a = Analysis(protocol_id=p.id, dataset_id=d.id, status="done")
        a.findings.append(
            FindingRow(
                analyzer="visit_windows", severity="minor", subject_id="1001",
                summary="s", detail="d", protocol_citation="c",
                data_citation={}, confidence=1.0,
            )
        )
        db.add(a)
        db.commit()
        db.delete(a)
        db.commit()
        assert db.query(FindingRow).count() == 0
    finally:
        db.close()
