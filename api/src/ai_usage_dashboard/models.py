from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_usage_dashboard.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_per_input_token: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_output_token: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="model"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="project"
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_models.id"), nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    model: Mapped["AIModel"] = relationship("AIModel", back_populates="usage_records")
    project: Mapped["Project | None"] = relationship(
        "Project", back_populates="usage_records"
    )
