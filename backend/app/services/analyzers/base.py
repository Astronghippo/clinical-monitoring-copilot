from __future__ import annotations

from typing import Literal, Protocol as Proto, runtime_checkable

from pydantic import BaseModel

from app.services.dataset_loader import PatientDataset
from app.services.protocol_parser import ProtocolSpec


class Finding(BaseModel):
    """Single protocol deviation discovered by an analyzer."""
    analyzer: Literal["visit_windows", "completeness", "eligibility"]
    severity: Literal["critical", "major", "minor"]
    subject_id: str
    summary: str
    detail: str
    protocol_citation: str
    data_citation: dict
    confidence: float


@runtime_checkable
class Analyzer(Proto):
    name: str

    def run(self, *, spec: ProtocolSpec, dataset: PatientDataset) -> list[Finding]:
        ...
