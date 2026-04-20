"""Weekly narrative digest — 2-paragraph prose summary of an analysis's findings.

Useful for emailing to study management or keeping a record of monitoring status.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.services.llm_client import LLMClient

_SYSTEM = """\
You are a clinical data monitoring report writer. Your job is to write a concise
weekly monitoring digest for study management.

Write exactly two paragraphs:
1. Overall status: total findings, breakdown by severity (critical/major/minor),
   resolution rate, and any notable patterns across subjects or sites.
2. Recommended actions: what the team should prioritise this week, in order of
   urgency.

Use precise clinical language. Be factual and data-driven. Do not add headers,
bullet points, or markdown — plain prose only.
"""


def draft_digest(
    *,
    study_id: str,
    findings: list[dict[str, Any]],
    llm: Any | None = None,
) -> str:
    """Return a 2-paragraph narrative digest for `study_id`'s findings.

    Parameters
    ----------
    study_id:   Protocol study identifier.
    findings:   List of finding dicts (analyzer, severity, subject_id, summary, status).
    llm:        Injectable LLM client (for tests).
    """
    llm = llm or LLMClient()

    total = len(findings)
    severity_counts = Counter(f.get("severity", "unknown") for f in findings)
    status_counts = Counter(f.get("status", "unknown") for f in findings)

    # Build a compact summary list for the LLM (avoid sending full detail field).
    compact_findings = [
        {
            "analyzer": f.get("analyzer"),
            "severity": f.get("severity"),
            "subject_id": f.get("subject_id"),
            "summary": f.get("summary"),
            "status": f.get("status"),
        }
        for f in findings
    ]

    user = json.dumps(
        {
            "study_id": study_id,
            "total_findings": total,
            "severity_counts": dict(severity_counts),
            "status_counts": dict(status_counts),
            "findings": compact_findings,
        },
        indent=2,
    )

    return llm.text_completion(system=_SYSTEM, user=user, max_tokens=512)
