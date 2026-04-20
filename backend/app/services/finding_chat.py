"""Conversational chat grounded in a single finding.

The LLM receives the full finding context in its system prompt and can
drill deeper, explain the rationale, surface related data points, and
suggest next-step actions for the clinical research associate.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.llm_client import LLMClient

_SYSTEM_TEMPLATE = """\
You are a clinical data monitoring assistant helping a Clinical Research Associate (CRA)
investigate a specific protocol deviation or data finding.

## Finding under review

- **Summary:** {summary}
- **Analyzer:** {analyzer}
- **Severity:** {severity}
- **Subject ID:** {subject_id}
- **Confidence:** {confidence_pct}%

### Explanation
{detail}

### Protocol citation
{protocol_citation}

### Supporting data
```json
{data_citation_json}
```

## Your role
Answer the CRA's questions about this finding in clear, concise clinical language.
- Explain *why* the finding was flagged, grounded in the data above.
- Surface related data points or patterns when relevant.
- Suggest concrete next-step actions (e.g., request source documents, contact site).
- Be honest about uncertainty — if you need more data say so.
- Keep replies to 1-4 short paragraphs unless the CRA asks for more detail.
"""


def chat_with_finding(
    *,
    finding: dict[str, Any],
    message: str,
    history: list[dict[str, str]],
    llm: Any | None = None,
) -> str:
    """Return Claude's reply to `message` in the context of `finding`.

    Parameters
    ----------
    finding:
        Dict representation of a FindingRow (id, analyzer, severity,
        subject_id, summary, detail, protocol_citation, data_citation,
        confidence).
    message:
        The CRA's latest question or message.
    history:
        Prior turns as ``[{"role": "user"|"assistant", "content": "…"}, …]``.
    llm:
        Injectable LLM client (for tests). Falls back to a real LLMClient.
    """
    llm = llm or LLMClient()

    system = _SYSTEM_TEMPLATE.format(
        summary=finding.get("summary", ""),
        analyzer=finding.get("analyzer", ""),
        severity=finding.get("severity", ""),
        subject_id=finding.get("subject_id", ""),
        confidence_pct=round((finding.get("confidence", 0) or 0) * 100),
        detail=finding.get("detail", ""),
        protocol_citation=finding.get("protocol_citation", ""),
        data_citation_json=json.dumps(finding.get("data_citation", {}), indent=2),
    )

    messages = list(history) + [{"role": "user", "content": message}]
    return llm.chat_completion(system=system, messages=messages)
