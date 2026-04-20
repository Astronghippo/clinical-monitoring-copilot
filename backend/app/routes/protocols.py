"""Protocol upload + async parse.

The upload endpoint responds immediately after extracting text from the PDF;
Claude-powered parsing runs as a FastAPI BackgroundTask and writes its result
back into the Protocol row. The frontend polls GET /protocols/{id} until
`parse_status` is "done" or "error".
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models import Protocol
from app.schemas import ProtocolOut
from app.services.protocol_parser import (
    ProtocolSpec,
    extract_text_from_pdf_bytes,
    parse_protocol_text,
)
from app.services.protocol_summary import summarize_protocol_text


router = APIRouter(prefix="/protocols", tags=["protocols"])


class SpecPatch(BaseModel):
    spec_json: dict


def _parse_in_background(protocol_id: int) -> None:
    """Background task: call Claude to build ProtocolSpec + narrative summary.

    Two Claude calls in sequence (not parallel, for rate-limit friendliness):
    1. spec extraction (visits + eligibility) — structured data for analyzers
    2. summary extraction (title, phase, endpoints, etc.) — narrative overview

    If the spec call succeeds but summary fails, we still mark parse_status=done
    and leave summary_json=None (the frontend will simply not render the
    overview card). If spec fails, the whole parse is flagged as error.
    """
    db = SessionLocal()
    try:
        p = db.get(Protocol, protocol_id)
        if p is None:
            return
        try:
            spec = parse_protocol_text(p.raw_text)
            p.study_id = spec.study_id or "(unknown)"
            p.spec_json = spec.model_dump()

            # Best-effort summary — doesn't fail the parse if it errors.
            try:
                p.summary_json = summarize_protocol_text(p.raw_text)
            except Exception:  # noqa: BLE001
                p.summary_json = None

            p.parse_status = "done"
            p.parse_error = None
        except Exception as e:  # noqa: BLE001 — surface any spec-parse error to UI
            p.parse_status = "error"
            p.parse_error = f"{type(e).__name__}: {e}"
        db.commit()
    finally:
        db.close()


@router.post("", response_model=ProtocolOut)
async def upload_protocol(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Protocol:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF required")
    data = await file.read()
    try:
        text = extract_text_from_pdf_bytes(data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"PDF extraction failed: {type(e).__name__}: {e}")

    p = Protocol(
        study_id="(parsing)",
        filename=file.filename,
        raw_text=text,
        spec_json=None,
        parse_status="parsing",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    background.add_task(_parse_in_background, p.id)
    return p


@router.get("/{protocol_id}", response_model=ProtocolOut)
def get_protocol(protocol_id: int, db: Session = Depends(get_db)) -> Protocol:
    p = db.get(Protocol, protocol_id)
    if p is None:
        raise HTTPException(404, "Protocol not found")
    return p


@router.get("", response_model=list[ProtocolOut])
def list_protocols(db: Session = Depends(get_db)) -> list[Protocol]:
    return db.query(Protocol).order_by(Protocol.id.desc()).all()


@router.patch("/{protocol_id}/spec", response_model=ProtocolOut)
def patch_protocol_spec(
    protocol_id: int,
    body: SpecPatch,
    db: Session = Depends(get_db),
) -> Protocol:
    p = db.get(Protocol, protocol_id)
    if p is None:
        raise HTTPException(404, "Protocol not found")
    if p.parse_status == "parsing":
        raise HTTPException(status_code=409, detail="Protocol is still being parsed; retry after parse completes")
    try:
        validated_spec = ProtocolSpec.model_validate(body.spec_json)
    except ValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    p.study_id = validated_spec.study_id
    p.spec_json = body.spec_json
    db.commit()
    db.refresh(p)
    return p
