from __future__ import annotations

import io
import re
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


# Above this size (chars), we stop sending the full protocol to the LLM and
# instead extract only the sections likely to contain visit schedule +
# eligibility criteria. Keeps us under per-minute input-token rate limits.
_MAX_FULL_CHARS = 40_000

# Each matched section produces a window starting 500 chars before the match
# and extending 6000 chars after — enough to capture a typical section.
_WINDOW_BEFORE = 500
_WINDOW_AFTER = 6000

# Case-insensitive section-heading patterns. Narrow enough to avoid false
# positives (e.g., "flow chart" alone is too generic — 45+ hits in one BI
# protocol — so we require the more specific sibling terms).
_SECTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"schedule\s+of\s+(assessments?|events?|visits?|(trial\s+)?procedures?)", re.IGNORECASE),
    re.compile(r"visit\s+schedule", re.IGNORECASE),
    re.compile(r"inclusion\s+criteria", re.IGNORECASE),
    re.compile(r"exclusion\s+criteria", re.IGNORECASE),
    re.compile(r"eligibility\s+criteria", re.IGNORECASE),
    re.compile(r"main\s+(inclusion|exclusion)\s+criteria", re.IGNORECASE),
    re.compile(r"study\s+(design|objectives?)", re.IGNORECASE),  # often precedes schedule
)


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Return concatenated text extracted from every page of the PDF."""
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping / adjacent (start, end) ranges."""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [ranges[0]]
    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 200:  # treat near-adjacent as overlapping
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def extract_relevant_excerpt(text: str, max_chars: int = _MAX_FULL_CHARS) -> str:
    """Return an excerpt containing likely-relevant sections of a long protocol.

    Strategy:
    1. Find every match of section-heading patterns (Schedule of X, Inclusion
       Criteria, etc.).
    2. For each match, take a window [match_pos - 500, match_pos + 6000].
    3. Merge overlapping windows.
    4. If nothing matched, fall back to the leading `max_chars` of text.
    5. If the merged excerpt exceeds `max_chars`, truncate.

    The full text is still stored in the DB — this only affects what we send
    to the LLM.
    """
    windows: list[tuple[int, int]] = []
    for pattern in _SECTION_PATTERNS:
        for m in pattern.finditer(text):
            start = max(0, m.start() - _WINDOW_BEFORE)
            end = min(len(text), m.start() + _WINDOW_AFTER)
            windows.append((start, end))

    if not windows:
        return text[:max_chars]

    merged = _merge_ranges(windows)
    excerpt = "\n\n---\n\n".join(text[s:e] for s, e in merged)

    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars]
    return excerpt


# Minimum extracted-text length that counts as a "good" pypdf extraction.
# Below this we assume the PDF is scanned or has complex layout and fall back
# to Claude Vision.
_MIN_VISION_FALLBACK_CHARS = 500


def parse_protocol_pdf_bytes(
    pdf_bytes: bytes,
    *,
    llm: LLMClient | None = None,
    vision_llm: LLMClient | None = None,
) -> ProtocolSpec:
    """Parse a protocol PDF, falling back to Claude Vision when pypdf is sparse.

    Steps:
    1. Extract text with pypdf.
    2. If len(text) < _MIN_VISION_FALLBACK_CHARS and vision_llm is provided,
       call vision_llm.pdf_text_extraction(pdf_bytes) to obtain richer text.
    3. Parse via the normal parse_protocol_text() path.
    """
    text = extract_text_from_pdf_bytes(pdf_bytes)
    if len(text.strip()) < _MIN_VISION_FALLBACK_CHARS and vision_llm is not None:
        text = vision_llm.pdf_text_extraction(pdf_bytes)
    return parse_protocol_text(text, llm=llm)


def parse_protocol_text(text: str, *, llm: LLMClient | None = None) -> ProtocolSpec:
    """Ask the LLM to extract a structured ProtocolSpec from raw protocol text.

    For large protocols (> _MAX_FULL_CHARS) we excerpt only the sections
    likely to contain visit schedule + eligibility criteria, to stay under
    per-minute input-token rate limits.

    max_tokens=16000: real oncology / Phase III protocols can have 10-20+
    visits and 25-40 eligibility criteria — the JSON output regularly needs
    5000+ tokens. The 4096 default was truncating mid-value.
    """
    llm = llm or LLMClient()
    prompt_text = (
        extract_relevant_excerpt(text) if len(text) > _MAX_FULL_CHARS else text
    )
    raw = llm.json_completion(system=_PROMPT, user=prompt_text, max_tokens=16000)
    return ProtocolSpec.model_validate(raw)
