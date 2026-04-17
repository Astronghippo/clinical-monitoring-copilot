from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Protocol(Base):
    __tablename__ = "protocols"
    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    spec_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    storage_path: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_id: Mapped[int] = mapped_column(ForeignKey("protocols.id"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    findings: Mapped[list["FindingRow"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class FindingRow(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    analyzer: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    subject_id: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text)
    protocol_citation: Mapped[str] = mapped_column(String(128))
    data_citation: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    analysis: Mapped[Analysis] = relationship(back_populates="findings")
