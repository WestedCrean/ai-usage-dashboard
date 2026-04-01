from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── AIModel ──────────────────────────────────────────────────────────────────


class AIModelCreate(BaseModel):
    name: str
    provider: str
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0


class AIModelRead(BaseModel):
    id: int
    name: str
    provider: str
    cost_per_input_token: float
    cost_per_output_token: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Project ───────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    team: str = ""
    description: str = ""


class ProjectRead(BaseModel):
    id: int
    name: str
    team: str | None
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── UsageRecord ───────────────────────────────────────────────────────────────


class UsageRecordCreate(BaseModel):
    model_id: int
    project_id: int | None = None
    timestamp: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float | None = None
    success: bool = True
    raw_metadata: dict[str, Any] | None = None


class UsageRecordRead(BaseModel):
    id: int
    model_id: int
    project_id: int | None
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    latency_ms: float | None
    success: bool
    cost: float
    raw_metadata: dict[str, Any] | None

    model_config = ConfigDict(from_attributes=True)


# ── Summary ───────────────────────────────────────────────────────────────────


class UsageSummary(BaseModel):
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    avg_latency_ms: float | None
    success_rate: float
