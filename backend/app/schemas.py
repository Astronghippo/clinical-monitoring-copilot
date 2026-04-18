from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analyzer: Literal["visit_windows", "completeness", "eligibility"]
    severity: Literal["critical", "major", "minor"]
    subject_id: str
    summary: str
    detail: str
    protocol_citation: str
    data_citation: dict
    confidence: float


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    protocol_id: int
    dataset_id: int
    status: str
    created_at: datetime
    findings: list[FindingOut] = []


class AnalysisSummary(BaseModel):
    """Light projection for the list/history view — no findings payload."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    protocol_id: int
    dataset_id: int
    status: str
    created_at: datetime
    study_id: str | None = None
    finding_count: int = 0
    counts: dict[str, int] = {}  # {"critical": N, "major": N, "minor": N}


class ProtocolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    study_id: str
    filename: str
    created_at: datetime
    # Parsed ProtocolSpec (visits + eligibility). Filled asynchronously by a
    # background task; until parse_status == "done", spec_json is None.
    spec_json: dict | None = None
    # High-level human-readable summary (title, phase, indication, etc.).
    # Filled by the same background task as spec_json.
    summary_json: dict | None = None
    parse_status: str = "done"  # "parsing" | "done" | "error"
    parse_error: str | None = None


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
