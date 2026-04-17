from __future__ import annotations

import json
from pathlib import Path

from app.services.analyzers.base import Finding
from app.services.dataset_loader import PatientDataset
from app.services.llm_client import LLMClient
from app.services.protocol_parser import ProtocolSpec


DEFAULT_TESTCODE_MAP: dict[str, str] = {
    "SYSBP": "Vitals", "DIABP": "Vitals", "PULSE": "Vitals", "TEMP": "Vitals",
    "HBA1C": "Labs", "GLUC": "Labs", "CREAT": "Labs", "ALT": "Labs", "AST": "Labs",
    "ECGINT": "ECG", "QTCF": "ECG", "HR": "ECG",
}


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "analyze_completeness.md"
)
_PROMPT = _PROMPT_PATH.read_text()


class CompletenessAnalyzer:
    """LLM-driven check that every required procedure was captured at each visit."""
    name = "completeness"

    def __init__(
        self,
        llm: LLMClient | None = None,
        testcode_map: dict[str, str] | None = None,
    ) -> None:
        self._llm = llm or LLMClient()
        self._map = testcode_map or DEFAULT_TESTCODE_MAP

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:
        findings: list[Finding] = []
        for sid in dataset.subjects():
            visits = dataset.visits_for(sid)
            for _, row in visits.iterrows():
                vdef = next((v for v in spec.visits if v.name == row["VISIT"]), None)
                if not vdef or not vdef.required_procedures:
                    continue
                captured = dataset.procedures_at(sid, vdef.name)
                payload = {
                    "subject_id": sid,
                    "visit": vdef.name,
                    "required": vdef.required_procedures,
                    "captured_testcodes": list(captured),
                    "testcode_to_procedure": self._map,
                }
                result = self._llm.json_completion(
                    system=_PROMPT, user=json.dumps(payload)
                )
                for proc in result.get("missing", []):
                    findings.append(Finding(
                        analyzer="completeness",
                        severity="major",
                        subject_id=sid,
                        summary=f"Subject {sid} {vdef.visit_id} missing required: {proc}",
                        detail=result.get("reasoning", ""),
                        protocol_citation=f"Schedule of Assessments, visit {vdef.visit_id}",
                        data_citation={
                            "domain": "VS", "usubjid": sid,
                            "visit": vdef.name, "captured": list(captured),
                        },
                        confidence=0.85,
                    ))
        return findings
