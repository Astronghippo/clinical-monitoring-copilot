"""Finding-level endpoints (e.g., draft a query letter for a specific finding)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, Dataset, FindingRow, Protocol
from app.services.dataset_loader import load_dataset
from app.services.query_letter import draft_query_letter


router = APIRouter(prefix="/findings", tags=["findings"])


class QueryLetterOut(BaseModel):
    subject_line: str
    body: str
    reply_by: str


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
