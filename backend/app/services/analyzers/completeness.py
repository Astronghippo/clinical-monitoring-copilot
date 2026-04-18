from __future__ import annotations

import json
from pathlib import Path

from app.services.analyzers.base import Finding
from app.services.dataset_loader import PatientDataset, normalize_visit_name
from app.services.llm_client import LLMClient
from app.services.protocol_parser import ProtocolSpec


# Expanded SDTM controlled-terminology testcode → procedure-category map.
# Covers common vitals, clinical labs, ECG, and basic physical exam codes.
# Unknown codes still reach the LLM, which can reason about them from context.
DEFAULT_TESTCODE_MAP: dict[str, str] = {
    # --- Vitals ---
    "SYSBP": "Vitals", "DIABP": "Vitals", "PULSE": "Vitals", "TEMP": "Vitals",
    "RESP": "Vitals", "HEIGHT": "Vitals", "WEIGHT": "Vitals", "BMI": "Vitals",
    "O2SAT": "Vitals", "SPO2": "Vitals", "HR": "Vitals", "HEARTRT": "Vitals",
    # --- Labs (chemistry + hematology) ---
    "HBA1C": "Labs", "GLUC": "Labs", "GLUCOSE": "Labs",
    "CREAT": "Labs", "CREATININE": "Labs", "BUN": "Labs",
    "ALT": "Labs", "AST": "Labs", "ALP": "Labs", "LDH": "Labs",
    "CHOL": "Labs", "HDL": "Labs", "LDL": "Labs", "TRIG": "Labs",
    "HGB": "Labs", "HEMOGLOBIN": "Labs", "HCT": "Labs", "HEMATOCRIT": "Labs",
    "WBC": "Labs", "RBC": "Labs", "PLAT": "Labs", "PLATELET": "Labs",
    "NA": "Labs", "SODIUM": "Labs", "K": "Labs", "POTASSIUM": "Labs",
    "CL": "Labs", "CHLORIDE": "Labs", "CA": "Labs", "CALCIUM": "Labs",
    "ALB": "Labs", "ALBUMIN": "Labs", "TBILI": "Labs", "DBILI": "Labs",
    "INR": "Labs", "PTT": "Labs", "TSH": "Labs", "T3": "Labs", "T4": "Labs",
    "CRP": "Labs", "ESR": "Labs", "LAC": "Labs", "URIC": "Labs",
    # --- ECG ---
    "ECGINT": "ECG", "QTCF": "ECG", "QT": "ECG", "QTC": "ECG",
    "PR": "ECG", "QRS": "ECG", "ECG": "ECG", "EKG": "ECG",
    # --- Physical exam / basic ---
    "PE": "Physical Exam", "PHYSEX": "Physical Exam",
    # --- Imaging (coarse) ---
    "CT": "Imaging", "MRI": "Imaging", "XRAY": "Imaging", "ULTRASOUND": "Imaging",
}


_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "prompts" / "analyze_completeness.md"
)
_PROMPT = _PROMPT_PATH.read_text()


class CompletenessAnalyzer:
    """LLM-driven check that every required procedure was captured at each visit.

    Batched: one LLM call per subject (bundles all their visits), rather than
    one call per subject×visit. Reduces API volume ~5x and sidesteps rate limits.
    """
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
        visits_by_norm = {normalize_visit_name(v.name): v for v in spec.visits}

        for sid in dataset.subjects():
            subject_visits = dataset.visits_for(sid)
            # Build the per-subject batch payload: one row per (visit-with-required-procs).
            batch_rows: list[dict] = []
            vdefs: list = []
            for _, row in subject_visits.iterrows():
                vdef = visits_by_norm.get(normalize_visit_name(row["VISIT"]))
                if not vdef or not vdef.required_procedures:
                    continue
                captured = dataset.procedures_at(sid, vdef.name)
                batch_rows.append({
                    "visit_id": vdef.visit_id,
                    "visit": vdef.name,
                    "required": vdef.required_procedures,
                    "captured_testcodes": list(captured),
                })
                vdefs.append((vdef, captured))

            if not batch_rows:
                continue

            payload = {
                "subject_id": sid,
                "testcode_to_procedure": self._map,
                "visits": batch_rows,
            }
            # max_tokens=8000: one per-subject call can cover 10+ visits;
            # each visit returns up to ~100 tokens of reasoning/missing list.
            result = self._llm.json_completion(
                system=_PROMPT, user=json.dumps(payload), max_tokens=8000,
            )

            # Match response entries back to the vdefs by position OR by visit_id.
            visit_results = result.get("visits", [])
            by_id = {entry.get("visit_id"): entry for entry in visit_results}

            for vdef, captured in vdefs:
                entry = by_id.get(vdef.visit_id)
                if entry is None:
                    continue
                for proc in entry.get("missing", []):
                    findings.append(Finding(
                        analyzer="completeness",
                        severity="major",
                        subject_id=sid,
                        summary=f"Subject {sid} {vdef.visit_id} missing required: {proc}",
                        detail=entry.get("reasoning", ""),
                        protocol_citation=f"Schedule of Assessments, visit {vdef.visit_id}",
                        data_citation={
                            "domain": "VS", "usubjid": sid,
                            "visit": vdef.name, "captured": list(captured),
                        },
                        confidence=0.85,
                    ))
        return findings
