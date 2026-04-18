"""LLM-powered extraction of high-level protocol context.

Complementary to protocol_parser (which extracts the *structured* spec:
visits, windows, I/E criteria). This service extracts the human-readable
*narrative* context: title, phase, indication, design, arms, endpoints,
sponsor, sample size, notable aspects.

Strategy for large protocols: title page + synopsis + study-design sections
almost always live in the first 15-25 pages of a protocol, so we send the
leading portion of the text rather than hunting for scattered keyword matches.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.llm_client import LLMClient


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "summarize_protocol.md"
)
_PROMPT = _PROMPT_PATH.read_text()

# Cap the leading slice we send to the summary prompt. Protocol synopses
# almost always fit inside the first ~30K chars (~7.5K tokens), well under
# the 30K input-TPM rate limit alongside the spec-extraction call.
_MAX_SUMMARY_CHARS = 30_000


def summary_excerpt(text: str, max_chars: int = _MAX_SUMMARY_CHARS) -> str:
    """Return the leading portion of the protocol text, capped at max_chars."""
    return text[:max_chars]


def summarize_protocol_text(text: str, *, llm: LLMClient | None = None) -> dict[str, Any]:
    """Return a dict of high-level protocol metadata, suitable for display.

    Fields follow the schema in prompts/summarize_protocol.md. Any missing
    fields are normalized to None so downstream code can rely on the shape.
    """
    llm = llm or LLMClient()
    prompt_text = summary_excerpt(text)
    raw = llm.json_completion(system=_PROMPT, user=prompt_text)

    # Normalize the shape defensively (LLM might omit fields).
    def _get(key, default=None):
        val = raw.get(key, default)
        return val if val not in ("", "null") else default

    return {
        "study_id": _get("study_id"),
        "title": _get("title"),
        "short_description": _get("short_description"),
        "phase": _get("phase"),
        "indication": _get("indication"),
        "sponsor": _get("sponsor"),
        "design": _get("design"),
        "arms": raw.get("arms") or [],
        "primary_endpoint": _get("primary_endpoint"),
        "secondary_endpoints": raw.get("secondary_endpoints") or [],
        "treatment_duration": _get("treatment_duration"),
        "sample_size": raw.get("sample_size"),
        "notable_aspects": _get("notable_aspects"),
    }
