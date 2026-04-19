"""Generate a single-file PDF report of an analysis's findings.

Uses reportlab. Output goes to an in-memory bytes buffer.
"""
from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from app.models import Analysis, Protocol


_SEV_COLOR = {
    "critical": colors.HexColor("#dc2626"),
    "major": colors.HexColor("#d97706"),
    "minor": colors.HexColor("#64748b"),
}


def render_analysis_pdf(analysis: Analysis, protocol: Protocol) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = []
    display_name = analysis.name or f"Analysis #{analysis.id}"
    story.append(Paragraph(display_name, h1))
    story.append(Paragraph(f"Protocol: <b>{protocol.study_id}</b>", body))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body))
    story.append(Spacer(1, 12))

    counts = {"critical": 0, "major": 0, "minor": 0}
    for f in analysis.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary_rows = [
        ["Severity", "Count"],
        ["Critical", str(counts["critical"])],
        ["Major", str(counts["major"])],
        ["Minor", str(counts["minor"])],
        ["Total", str(sum(counts.values()))],
    ]
    t = Table(summary_rows, colWidths=[2 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 18))

    sev_order = ["critical", "major", "minor"]
    by_sev: dict[str, list] = {k: [] for k in sev_order}
    for f in analysis.findings:
        by_sev.setdefault(f.severity, []).append(f)

    for sev in sev_order:
        if not by_sev.get(sev):
            continue
        color = _SEV_COLOR[sev].hexval()
        story.append(Paragraph(
            f"<font color='{color}'>{sev.upper()}</font> ({len(by_sev[sev])})",
            h2,
        ))
        for f in by_sev[sev]:
            story.append(Paragraph(
                f"<b>Subject {f.subject_id}</b> \u2014 {f.summary}", body,
            ))
            story.append(Paragraph(f"{f.detail}", body))
            story.append(Paragraph(
                f"<i>Protocol: {f.protocol_citation} \u00b7 Confidence {int(f.confidence * 100)}%</i>",
                body,
            ))
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 12))

    doc.build(story)
    return buf.getvalue()
