from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pypdf import PdfReader

from app.services.llm_client import LLMClient


class VisitDef(BaseModel):
    visit_id: str
    name: str
    nominal_day: int
    window_minus_days: int = 0
    window_plus_days: int = 0
    required_procedures: list[str] = []


class EligibilityCriterion(BaseModel):
    criterion_id: str
    kind: Literal["inclusion", "exclusion"]
    text: str
    structured_check: dict | None = None


class ProtocolSpec(BaseModel):
    study_id: str
    visits: list[VisitDef]
    eligibility: list[EligibilityCriterion]
    source_pages: dict[str, list[int]] = {}


_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extract_protocol.md"
_PROMPT = _PROMPT_PATH.read_text()


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Return concatenated text extracted from every page of the PDF."""
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def parse_protocol_text(text: str, *, llm: LLMClient | None = None) -> ProtocolSpec:
    """Ask the LLM to extract a structured ProtocolSpec from raw protocol text."""
    llm = llm or LLMClient()
    raw = llm.json_completion(system=_PROMPT, user=text)
    return ProtocolSpec.model_validate(raw)
