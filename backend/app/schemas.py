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


class ProtocolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    study_id: str
    filename: str
    created_at: datetime


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
