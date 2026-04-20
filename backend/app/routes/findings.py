"""Finding-level endpoints (e.g., draft a query letter for a specific finding)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, Dataset, FindingRow, Protocol
from app.schemas import FindingOut, FindingStatusUpdate, FindingBulkStatusUpdate
from app.services import audit as audit_service
from app.services.dataset_loader import load_dataset
from app.services.finding_chat import chat_with_finding
from app.services.llm_client import LLMClient
from app.services.query_letter import draft_query_letter

# Module-level LLM instance so tests can monkeypatch it.
_chat_llm: LLMClient | None = None

router = APIRouter(prefix="/findings", tags=["findings"])


class QueryLetterOut(BaseModel):
    subject_line: str
    body: str
    reply_by: str


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatIn(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatOut(BaseModel):
    reply: str


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: int, db: Session = Depends(get_db)) -> FindingRow:
    f = db.get(FindingRow, finding_id)
    if f is None:
        raise HTTPException(404, "Finding not found")
    return f


@router.patch("/{finding_id}", response_model=FindingOut)
def update_finding(
    finding_id: int,
    body: FindingStatusUpdate,
    db: Session = Depends(get_db),
) -> FindingRow:
    f = db.get(FindingRow, finding_id)
    if f is None:
        raise HTTPException(404, "Finding not found")
    before = {
        "status": f.status, "assignee": f.assignee, "notes": f.notes,
    }
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(f, k, v)
    audit_service.record(
        db, event_type="finding.update",
        subject_kind="finding", subject_id=finding_id,
        before=before, after=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(f)
    return f


@router.post("/bulk-status")
def bulk_status_update(
    body: FindingBulkStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    if not body.finding_ids:
        return {"updated": 0}
    n = (
        db.query(FindingRow)
        .filter(FindingRow.id.in_(body.finding_ids))
        .update({"status": body.status}, synchronize_session=False)
    )
    db.commit()
    return {"updated": n}


@router.post("/{finding_id}/query-letter", response_model=QueryLetterOut)
def generate_query_letter(
    finding_id: int,
    db: Session = Depends(get_db),
) -> QueryLetterOut:
    """Return a drafted site-facing query letter for this finding."""
    finding = db.get(FindingRow, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found")

    analysis = db.get(Analysis, finding.analysis_id)
    protocol = db.get(Protocol, analysis.protocol_id) if analysis else None
    dataset = db.get(Dataset, analysis.dataset_id) if analysis else None
    if protocol is None or dataset is None:
        raise HTTPException(404, "Associated protocol or dataset missing")

    # Look up the site id from the subject's demographics row (if available).
    site_id = "UNKNOWN-SITE"
    try:
        ds = load_dataset(dataset.storage_path)
        demo = ds.demographics(finding.subject_id)
        site_id = str(demo.get("SITEID", "UNKNOWN-SITE"))
    except Exception:
        pass  # best-effort — don't fail the letter just because site lookup didn't work

    letter = draft_query_letter(
        study_id=protocol.study_id,
        site_id=site_id,
        finding={
            "analyzer": finding.analyzer,
            "severity": finding.severity,
            "subject_id": finding.subject_id,
            "summary": finding.summary,
            "detail": finding.detail,
            "protocol_citation": finding.protocol_citation,
            "data_citation": finding.data_citation,
        },
    )
    return QueryLetterOut(**letter)


@router.post("/{finding_id}/chat", response_model=ChatOut)
def chat_finding(
    finding_id: int,
    body: ChatIn,
    db: Session = Depends(get_db),
) -> ChatOut:
    """Ask a question about a specific finding; Claude replies with deeper analysis."""
    finding = db.get(FindingRow, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found")

    reply = chat_with_finding(
        finding={
            "id": finding.id,
            "analyzer": finding.analyzer,
            "severity": finding.severity,
            "subject_id": finding.subject_id,
            "summary": finding.summary,
            "detail": finding.detail,
            "protocol_citation": finding.protocol_citation,
            "data_citation": finding.data_citation,
            "confidence": finding.confidence,
        },
        message=body.message,
        history=[{"role": m.role, "content": m.content} for m in body.history],
        llm=_chat_llm,
    )
    return ChatOut(reply=reply)
