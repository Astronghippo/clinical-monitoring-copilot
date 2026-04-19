"""Plausibility Analyzer — deterministic rule-based vital-sign/lab plausibility check.

Flags measurements that are outside physiologically possible ranges. No LLM calls.
"""
from __future__ import annotations

from app.services.analyzers.base import Finding
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec


# ---------------------------------------------------------------------------
# Plausibility rules table
# Each entry: TESTCD (or alias) → (min, max, unit_hint)
# Multiple keys can map to the same rule (aliases).
# ---------------------------------------------------------------------------

_RULES: dict[str, tuple[float, float, str]] = {
    # Systolic blood pressure
    "SYSBP":   (50.0,  300.0, "mmHg"),
    # Diastolic blood pressure
    "DIABP":   (20.0,  200.0, "mmHg"),
    # Heart rate / pulse — several common TESTCDs
    "PULSE":   (20.0,  300.0, "bpm"),
    "HR":      (20.0,  300.0, "bpm"),
    "HEARTRT": (20.0,  300.0, "bpm"),
    # Temperature
    # NOTE: assumes Celsius; Fahrenheit would be 95–113°F
    "TEMP":    (32.0,  45.0,  "°C"),
    # Respiratory rate
    "RESP":    (5.0,   60.0,  "/min"),
    # HbA1c
    "HBA1C":   (2.0,   20.0,  "%"),
    # Glucose — two common TESTCDs
    # NOTE: assumes mmol/L; US sites may record glucose in mg/dL (range ~18–1080).
    # VSORRESU column would need to be read for unit-aware checking.
    "GLUC":    (1.0,   60.0,  "mmol/L"),
    "GLUCOSE": (1.0,   60.0,  "mmol/L"),
    # Anthropometrics
    "HEIGHT":  (50.0,  250.0, "cm"),
    "WEIGHT":  (2.0,   300.0, "kg"),
    "BMI":     (10.0,  80.0,  "kg/m²"),
}


def _severity(value: float, lo: float, hi: float) -> str:
    """Derive severity from how far outside the plausible range a value is.

    Special case: value == 0 when min > 0 → minor (likely missing data).
    Within ≤ 20% of range width outside bounds → major.
    Beyond 20% of range width outside bounds → critical.
    """
    if value == 0.0 and lo > 0:
        # Zero in a numeric VSORRES typically indicates the EDC was submitted without a value
        # (missing data), not a true physiological reading. Flag minor to distinguish from
        # a genuinely implausible non-zero value.
        return "minor"

    range_width = hi - lo
    threshold = range_width * 0.20

    if value < lo:
        overshoot = lo - value
    else:
        overshoot = value - hi

    if overshoot <= threshold:
        return "major"
    return "critical"


class PlausibilityAnalyzer:
    """Checks vital signs and lab values for biological implausibility."""

    name = "plausibility"

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:  # noqa: ARG002
        findings: list[Finding] = []

        if dataset.vs.empty:
            return findings

        # subjects() is keyed off demographics (DM domain) — the authoritative enrollment list.
        # Subjects in VS but not in DM are intentionally skipped (fragmented import edge case).
        for subject_id in dataset.subjects():
            subject_vs = dataset.vs[dataset.vs["USUBJID"].astype(str) == subject_id]

            for _, row in subject_vs.iterrows():
                testcd = str(row.get("VSTESTCD", "") or "").strip().upper()
                rule = _RULES.get(testcd)
                if rule is None:
                    continue  # unknown test — skip

                lo, hi, unit = rule

                raw = str(row.get("VSORRES", "") or "").strip()
                try:
                    value = float(raw)
                except (ValueError, TypeError):
                    continue  # non-numeric — skip silently

                if lo <= value <= hi:
                    continue  # within plausible range — no finding

                severity = _severity(value, lo, hi)

                visit = str(row.get("VISIT", "") or "").strip()
                vsdtc = str(row.get("VSDTC", "") or "").strip()

                summary = (
                    f"Subject {subject_id} {testcd} value {value:g} {unit} "
                    f"is outside plausible range [{lo:g}, {hi:g}]"
                )
                detail = (
                    f"Recorded value: {value} {unit}. "
                    f"Physiologically plausible range: [{lo}, {hi}] {unit}. "
                    f"Visit: {visit or 'N/A'}. Date: {vsdtc or 'N/A'}."
                )

                findings.append(Finding(
                    analyzer="plausibility",
                    severity=severity,
                    subject_id=subject_id,
                    summary=summary,
                    detail=detail,
                    protocol_citation="Plausibility rule: physiological range check",
                    data_citation={
                        "domain": "VS",
                        "usubjid": subject_id,
                        "vstestcd": testcd,
                        "vsorres": raw,
                        "visit": visit,
                        "vsdtc": vsdtc,
                    },
                    confidence=1.0,
                ))

        return findings
