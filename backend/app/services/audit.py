from __future__ import annotations
from sqlalchemy.orm import Session
from app.models import AuditEvent


def record(
    db: Session, *,
    event_type: str, subject_kind: str, subject_id: int,
    actor: str = "system", before=None, after=None,
) -> AuditEvent:
    e = AuditEvent(
        event_type=event_type, subject_kind=subject_kind,
        subject_id=subject_id, actor=actor,
        before=before, after=after,
    )
    db.add(e)
    # Caller commits alongside their own work.
    return e
