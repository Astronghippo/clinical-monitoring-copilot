from __future__ import annotations

from datetime import date, datetime

from app.services.analyzers.base import Finding
from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec, VisitDef


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(str(s)).date()


def _severity(delta_days: int, window_minus: int, window_plus: int) -> str:
    """How far outside the allowed window, in days, determines severity."""
    if delta_days > 0:
        over = max(0, delta_days - window_plus)
    else:
        over = max(0, -delta_days - window_minus)
    if over >= 7:
        return "critical"
    if over >= 3:
        return "major"
    return "minor"


class VisitWindowAnalyzer:
    """Deterministic date-math check that each visit falls within its protocol window."""
    name = "visit_windows"

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:
        findings: list[Finding] = []
        by_name = {v.name: v for v in spec.visits}
        baseline = next((v for v in spec.visits if v.nominal_day == 0), None)
        if baseline is None:
            return findings

        for sid in dataset.subjects():
            visits = dataset.visits_for(sid)
            if visits.empty:
                continue
            base_row = visits[visits["VISIT"] == baseline.name]
            if base_row.empty:
                continue
            base_date = _parse_date(base_row.iloc[0]["SVSTDTC"])

            for _, row in visits.iterrows():
                vdef: VisitDef | None = by_name.get(row["VISIT"])
                if not vdef or vdef.visit_id == baseline.visit_id:
                    continue
                actual = _parse_date(row["SVSTDTC"])
                actual_day = (actual - base_date).days
                delta = actual_day - vdef.nominal_day  # positive = late
                in_window = (-vdef.window_minus_days) <= delta <= vdef.window_plus_days
                if in_window:
                    continue
                direction = "late" if delta > 0 else "early"
                over = abs(delta) - (
                    vdef.window_plus_days if delta > 0 else vdef.window_minus_days
                )
                findings.append(Finding(
                    analyzer="visit_windows",
                    severity=_severity(delta, vdef.window_minus_days, vdef.window_plus_days),
                    subject_id=sid,
                    summary=f"Subject {sid} {vdef.visit_id} ({vdef.name}) {direction} by {over} day(s)",
                    detail=(
                        f"Nominal day: {vdef.nominal_day}. Actual: day {actual_day}. "
                        f"Allowed window: -{vdef.window_minus_days}/+{vdef.window_plus_days}. "
                        f"Delta: {delta:+d} days."
                    ),
                    protocol_citation=f"Schedule of Assessments, visit {vdef.visit_id}",
                    data_citation={
                        "domain": "SV", "usubjid": sid,
                        "visit": vdef.name, "svstdtc": str(actual),
                    },
                    confidence=1.0,
                ))
        return findings
