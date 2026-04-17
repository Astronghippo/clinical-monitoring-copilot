"""LLM-powered drafting of site-facing data query letters for a given finding."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import TypedDict

from app.services.llm_client import LLMClient


_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "draft_query_letter.md"
_PROMPT = _PROMPT_PATH.read_text()


class QueryLetter(TypedDict):
    subject_line: str
    body: str
    reply_by: str


def draft_query_letter(
    *,
    study_id: str,
    site_id: str,
    finding: dict,
    today: date | None = None,
    llm: LLMClient | None = None,
) -> QueryLetter:
    """Generate a professional data-query letter for a single finding.

    `finding` must be a dict with fields: analyzer, severity, subject_id,
    summary, detail, protocol_citation, data_citation.
    """
    today_iso = (today or date.today()).isoformat()
    payload = {
        "study_id": study_id,
        "site_id": site_id,
        "finding": finding,
        "today_iso": today_iso,
    }
    client = llm or LLMClient()
    result = client.json_completion(system=_PROMPT, user=json.dumps(payload, default=str))
    # Accept defensive defaults if the model omits a field.
    return {
        "subject_line": str(result.get("subject_line", "")),
        "body": str(result.get("body", "")),
        "reply_by": str(result.get("reply_by", "")),
    }
