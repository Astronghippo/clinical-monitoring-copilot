from __future__ import annotations

import json
import math
from pathlib import Path
from typing import cast

from app.services.analyzers.base import Finding
from app.services.dataset_loader import PatientDataset
from app.services.llm_client import LLMClient
from app.services.protocol_parser import ProtocolSpec


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "analyze_eligibility.md"
)
_PROMPT = _PROMPT_PATH.read_text()

_ALLOWED_SEV = {"critical", "major", "minor"}


def _json_safe(value):
    """Convert pandas NaN floats to None so json.dumps doesn't emit NaN."""
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


class EligibilityAnalyzer:
    """LLM-driven check that each subject's demographics satisfy I/E criteria."""
    name = "eligibility"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:
        findings: list[Finding] = []
        if not spec.eligibility:
            return findings
        criteria_payload = [c.model_dump() for c in spec.eligibility]

        for sid in dataset.subjects():
            demo = {k: _json_safe(v) for k, v in dataset.demographics(sid).items()}
            payload = {
                "subject_id": sid,
                "demographics": demo,
                "criteria": criteria_payload,
            }
            result = self._llm.json_completion(
                system=_PROMPT, user=json.dumps(payload, default=str)
            )
            for v in result.get("violations", []):
                sev = v.get("severity", "major")
                if sev not in _ALLOWED_SEV:
                    sev = "major"
                findings.append(Finding(
                    analyzer="eligibility",
                    severity=cast("str", sev),
                    subject_id=sid,
                    summary=(
                        f"Subject {sid} violates {v.get('kind', '?')} "
                        f"criterion {v.get('criterion_id', '?')}"
                    ),
                    detail=v.get("reason", ""),
                    protocol_citation=f"Eligibility, {v.get('criterion_id', '?')}",
                    data_citation={"domain": "DM", "usubjid": sid, "fields": demo},
                    confidence=0.8,
                ))
        return findings
