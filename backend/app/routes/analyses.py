from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, get_db
from app.models import Analysis, Dataset, FindingRow, Protocol
from app.schemas import AnalysisOut, AnalysisRename, AnalysisSummary
from app.services import audit as audit_service
from app.services.analyzers.completeness import CompletenessAnalyzer
from app.services.analyzers.eligibility import EligibilityAnalyzer
from app.services.analyzers.visit_windows import VisitWindowAnalyzer
from app.services.dataset_loader import load_dataset
from app.services.protocol_parser import ProtocolSpec
from app.services.report_pdf import render_analysis_pdf


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
    audit_service.record(
        db, event_type="analysis.run",
        subject_kind="analysis", subject_id=a.id,
        after={"protocol_id": a.protocol_id, "dataset_id": a.dataset_id},
    )
    db.commit()
    bg.add_task(_run_analysis, a.id)
    return a


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")
    return a


@router.get("/{analysis_id}/report.pdf")
def analysis_pdf(analysis_id: int, db: Session = Depends(get_db)) -> Response:
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")
    p = db.get(Protocol, a.protocol_id)
    if p is None:
        raise HTTPException(404, "Protocol missing")
    pdf = render_analysis_pdf(a, p)
    filename = f"{(a.name or f'analysis-{a.id}').replace(' ', '_')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.get("/{analysis_id}/sites")
def site_rollup(analysis_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Return per-site aggregation of findings for the given analysis.

    Each item: {site_id, subject_count, finding_count, deviation_rate, counts: {critical, major, minor}}
    Subjects whose SITEID is absent from demographics are grouped under "UNKNOWN".
    """
    a = db.get(Analysis, analysis_id)
    if a is None:
        raise HTTPException(404, "Not found")

    dataset_row = db.get(Dataset, a.dataset_id)
    if dataset_row is None:
        raise HTTPException(404, "Dataset not found")

    dataset = load_dataset(dataset_row.storage_path)

    # Build subject → site map from demographics.
    subject_to_site: dict[str, str] = {}
    for subj in dataset.subjects():
        demo = dataset.demographics(subj)
        subject_to_site[subj] = str(demo.get("SITEID") or "UNKNOWN") if demo.get("SITEID") else "UNKNOWN"

    # Aggregate: site → {subject_count, finding_count, severity counts}
    site_subjects: dict[str, set[str]] = {}
    site_findings: dict[str, int] = {}
    site_sev: dict[str, dict[str, int]] = {}

    # Pre-populate all sites from the demographics so sites with 0 findings appear.
    for subj, site in subject_to_site.items():
        site_subjects.setdefault(site, set()).add(subj)
        site_findings.setdefault(site, 0)
        site_sev.setdefault(site, {"critical": 0, "major": 0, "minor": 0})

    # Count findings per site.
    for f in a.findings:
        site = subject_to_site.get(f.subject_id, "UNKNOWN")
        # Ensure site exists even if subject wasn't in demographics.
        site_subjects.setdefault(site, set()).add(f.subject_id)
        site_findings[site] = site_findings.get(site, 0) + 1
        sev = site_sev.setdefault(site, {"critical": 0, "major": 0, "minor": 0})
        sev_key = f.severity if f.severity in ("critical", "major", "minor") else "minor"
        sev[sev_key] = sev.get(sev_key, 0) + 1

    results = []
    for site_id in sorted(site_subjects.keys()):
        n_subjects = len(site_subjects[site_id])
        n_findings = site_findings.get(site_id, 0)
        deviation_rate = n_findings / n_subjects if n_subjects > 0 else 0.0
        results.append({
            "site_id": site_id,
            "subject_count": n_subjects,
            "finding_count": n_findings,
            "deviation_rate": round(deviation_rate, 4),
            "counts": site_sev.get(site_id, {"critical": 0, "major": 0, "minor": 0}),
        })
    return results


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
