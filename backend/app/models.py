from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Protocol(Base):
    __tablename__ = "protocols"
    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[str] = mapped_column(String(64), default="(parsing)")
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    # Nullable: spec_json is populated asynchronously by a background task
    # after the upload responds, since Claude parsing can take 30-60s on
    # large protocols.
    spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(16), default="parsing")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
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
