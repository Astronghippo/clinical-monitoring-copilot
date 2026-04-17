from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Protocol
from app.schemas import ProtocolOut
from app.services.protocol_parser import (
    extract_text_from_pdf_bytes,
    parse_protocol_text,
)


router = APIRouter(prefix="/protocols", tags=["protocols"])


@router.post("", response_model=ProtocolOut)
async def upload_protocol(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Protocol:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF required")
    data = await file.read()
    text = extract_text_from_pdf_bytes(data)
    spec = parse_protocol_text(text)
    p = Protocol(
        study_id=spec.study_id,
        filename=file.filename,
        raw_text=text,
        spec_json=spec.model_dump(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("", response_model=list[ProtocolOut])
def list_protocols(db: Session = Depends(get_db)) -> list[Protocol]:
    return db.query(Protocol).order_by(Protocol.id.desc()).all()
