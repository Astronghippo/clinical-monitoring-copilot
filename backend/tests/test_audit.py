from app.services.audit import record
from app.models import AuditEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base


def test_record_creates_event():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    record(db, event_type="test", subject_kind="finding", subject_id=1, actor="alex")
    db.commit()
    assert db.query(AuditEvent).count() == 1
    e = db.query(AuditEvent).first()
    assert e.event_type == "test"
    assert e.actor == "alex"


def test_audit_list_endpoint_returns_events(client_with_sqlite):
    r = client_with_sqlite.get("/audit")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
