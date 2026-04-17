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

# Subjects per LLM call. 20 keeps the prompt under ~5K tokens for typical
# demographics payloads while still batching efficiently. Tune if needed.
_BATCH_SIZE = 20


def _json_safe(value):
    """Convert pandas NaN floats to None so json.dumps doesn't emit NaN."""
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class EligibilityAnalyzer:
    """LLM-driven check that each subject's demographics satisfy I/E criteria.

    Batched: sends up to _BATCH_SIZE subjects per LLM call. For a 20-subject
    trial that's 1 call (was 20). For 100 subjects, 5 calls (was 100).
    """
    name = "eligibility"

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:
        findings: list[Finding] = []
        if not spec.eligibility:
            return findings
        criteria_payload = [c.model_dump() for c in spec.eligibility]

        all_subjects = dataset.subjects()
        # Precompute demographics once per subject (for citation later too).
        demographics: dict[str, dict] = {
            sid: {k: _json_safe(v) for k, v in dataset.demographics(sid).items()}
            for sid in all_subjects
        }

        for chunk in _chunks(all_subjects, _BATCH_SIZE):
            payload = {
                "criteria": criteria_payload,
                "subjects": [
                    {"subject_id": sid, "demographics": demographics[sid]}
                    for sid in chunk
                ],
            }
            result = self._llm.json_completion(
                system=_PROMPT, user=json.dumps(payload, default=str)
            )

            # Map results back to findings. Tolerate missing entries (subject might
            # be omitted by the LLM — we skip rather than crash).
            for entry in result.get("results", []):
                sid = str(entry.get("subject_id", ""))
                if sid not in demographics:
                    continue
                for v in entry.get("violations", []):
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
                        data_citation={
                            "domain": "DM", "usubjid": sid,
                            "fields": demographics[sid],
                        },
                        confidence=0.8,
                    ))

        return findings
