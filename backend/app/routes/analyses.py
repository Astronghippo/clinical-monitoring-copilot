from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, get_db
from app.models import Analysis, Dataset, FindingRow, Protocol
from app.schemas import AnalysisOut, AnalysisRename, AnalysisSummary
from app.services.analyzers.completeness import CompletenessAnalyzer
from app.services.analyzers.eligibility import EligibilityAnalyzer
from app.services.analyzers.visit_windows import VisitWindowAnalyzer
from app.services.dataset_loader import load_dataset
from app.services.protocol_parser import ProtocolSpec


router = APIRouter(prefix="/analyses", tags=["analyses"])


class RunRequest(BaseModel):
    protocol_id: int
    dataset_id: int


def _run_analysis(analysis_id: int) -> None:
    """Background worker: load spec + dataset, run all analyzers, persist findings."""
    db = SessionLocal()
    try:
        a = db.get(Analysis, analysis_id)
        if a is None:
            return
        a.status = "running"
        db.commit()
        try:
            p = db.get(Protocol, a.protocol_id)
            d = db.get(Dataset, a.dataset_id)
            assert p is not None and d is not None
            spec = ProtocolSpec.model_validate(p.spec_json)
            dataset = load_dataset(d.storage_path)
            for analyzer in (
                VisitWindowAnalyzer(),
                CompletenessAnalyzer(),
                EligibilityAnalyzer(),
            ):
                for f in analyzer.run(spec=spec, dataset=dataset):
                    db.add(FindingRow(
                        analysis_id=a.id,
                        analyzer=f.analyzer,
                        severity=f.severity,
                        subject_id=f.subject_id,
                        summary=f.summary,
                        detail=f.detail,
                        protocol_citation=f.protocol_citation,
                        data_citation=f.data_citation,
                        confidence=f.confidence,
                    ))
            a.status = "done"
        except Exception as e:  # noqa: BLE001 — surface any analyzer/loader error to the UI
            a.status = "error"
            db.add(FindingRow(
                analysis_id=a.id,
                analyzer="visit_windows",
                severity="critical",
                subject_id="-",
                summary=f"Analysis failed: {type(e).__name__}",
                detail=str(e),
                protocol_citation="-",
                data_citation={},
                confidence=0.0,
            ))
        db.commit()
    finally:
        db.close()


@router.post("", response_model=AnalysisOut)
def create_analysis(
    req: RunRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Analysis:
    if db.get(Protocol, req.protocol_id) is None:
        raise HTTPException(404, "Protocol not found")
    if db.get(Dataset, req.dataset_id) is None:
        raise HTTPException(404, "Dataset not found")
    a = Analysis(
        protocol_id=req.protocol_id,
        dataset_id=req.dataset_id,
        status="pending",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    bg.add_task(_run_analysis, a.id)
    return a


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")
    return a


@router.patch("/{analysis_id}", response_model=AnalysisOut)
def rename_analysis(
    analysis_id: int,
    body: AnalysisRename,
    db: Session = Depends(get_db),
) -> Analysis:
    """Update the user-editable display name. Empty/null clears the name."""
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")
    # Normalize empty strings to None so the frontend can fall back to "Analysis #N".
    name = (body.name or "").strip() or None
    a.name = name
    db.commit()
    db.refresh(a)
    return a


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[AnalysisSummary]:
    """Return recent analyses newest-first with severity counts + protocol study_id.

    Uses SQL aggregation for counts so we don't load thousands of FindingRow
    objects just to count them for each analysis in the list.
    """
    # Aggregate severity counts per analysis in a single query.
    sev_rows = (
        db.query(
            FindingRow.analysis_id,
            FindingRow.severity,
            func.count(FindingRow.id),
        )
        .group_by(FindingRow.analysis_id, FindingRow.severity)
        .all()
    )
    counts_by_analysis: dict[int, dict[str, int]] = {}
    for analysis_id, severity, n in sev_rows:
        counts_by_analysis.setdefault(analysis_id, {})[severity] = n

    analyses = (
        db.query(Analysis)
        .order_by(Analysis.id.desc())
        .limit(limit)
        .all()
    )
    # Resolve protocol study_id in one batched query.
    proto_ids = {a.protocol_id for a in analyses}
    protos = {
        p.id: p.study_id
        for p in db.query(Protocol).filter(Protocol.id.in_(proto_ids)).all()
    }

    summaries: list[AnalysisSummary] = []
    for a in analyses:
        c = counts_by_analysis.get(a.id, {})
        total = sum(c.values())
        summaries.append(
            AnalysisSummary(
                id=a.id,
                protocol_id=a.protocol_id,
                dataset_id=a.dataset_id,
                status=a.status,
                name=a.name,
                created_at=a.created_at,
                study_id=protos.get(a.protocol_id),
                finding_count=total,
                counts={"critical": c.get("critical", 0),
                        "major": c.get("major", 0),
                        "minor": c.get("minor", 0)},
            )
        )
    return summaries


def _finding_template(f) -> str:
    """Strip subject-specific tokens so near-duplicate findings share a template.

    Example: "Subject 1001 V2 (Week 2) missing required: Labs" →
             "V2 (Week 2) missing required: Labs"
    """
    s = f.summary or ""
    s = re.sub(r"^Subject\s+\S+\s+", "", s)
    return s.strip()


@router.get("/{analysis_id}/grouped")
def grouped_findings(analysis_id: int, db: Session = Depends(get_db)) -> list[dict]:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")
    groups: dict[tuple[str, str, str], dict] = {}
    for f in a.findings:
        key = (_finding_template(f), f.analyzer, f.severity)
        g = groups.get(key)
        if g is None:
            groups[key] = {
                "template": key[0],
                "analyzer": key[1],
                "severity": key[2],
                "count": 1,
                "subject_ids": [f.subject_id],
                "finding_ids": [f.id],
            }
        else:
            g["count"] += 1
            g["subject_ids"].append(f.subject_id)
            g["finding_ids"].append(f.id)
    sev_order = {"critical": 0, "major": 1, "minor": 2}
    return sorted(
        groups.values(),
        key=lambda g: (sev_order.get(g["severity"], 99), -g["count"]),
    )
