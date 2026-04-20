"""Natural-language query → structured filter params translation.

Translates a free-text CRA query (e.g. "show critical eligibility findings
for open cases") into a dict of filter parameters that the front-end can
apply to the findings table.

Returned shape
--------------
{
    "analyzer": "visit_windows" | "completeness" | "eligibility" | "plausibility" | null,
    "severity": ["critical", "major", "minor"] | null,
    "status": ["open", "in_review", "resolved", "false_positive"] | null,
    "search_text": "<keyword>" | null,
}

Any field set to null means "no constraint on that dimension".
"""
from __future__ import annotations

import json
from typing import Any

from app.services.llm_client import LLMClient

_SYSTEM = """\
You translate a clinical data monitor's natural-language query into a JSON filter
object that narrows findings in a clinical trial monitoring system.

The filter object has these optional keys (use null when a dimension is not constrained):
- "analyzer": one of "visit_windows", "completeness", "eligibility", "plausibility", or null
- "severity": a list subset of ["critical", "major", "minor"], or null
- "status": a list subset of ["open", "in_review", "resolved", "false_positive"], or null
- "search_text": a keyword or phrase to search in subject_id and summary, or null

Rules:
- Return ONLY valid JSON — no prose, no markdown, no code fences.
- Use null for any dimension not mentioned or inferable.
- If the query asks about labs, out-of-range values, or vital signs → analyzer "plausibility".
- If the query asks about missing data, incomplete forms → analyzer "completeness".
- If the query asks about eligibility violations, inclusion/exclusion → analyzer "eligibility".
- If the query asks about visit timing, scheduling, windows → analyzer "visit_windows".
- "open" or "unresolved" → status ["open"].
- "in review" → status ["in_review"].
- "resolved" or "closed" → status ["resolved"].
"""


def translate_query_to_filters(
    *,
    query: str,
    llm: Any | None = None,
) -> dict[str, Any]:
    """Translate `query` into a structured filter dict.

    Parameters
    ----------
    query:  Free-text query from the CRA, e.g. "show all out-of-range labs".
    llm:    Injectable LLM client (for tests).
    """
    llm = llm or LLMClient()
    user = json.dumps({"query": query})
    raw = llm.json_completion(system=_SYSTEM, user=user, max_tokens=256)

    # Normalise — fill any missing keys with None.
    return {
        "analyzer": raw.get("analyzer"),
        "severity": raw.get("severity"),
        "status": raw.get("status"),
        "search_text": raw.get("search_text"),
    }
