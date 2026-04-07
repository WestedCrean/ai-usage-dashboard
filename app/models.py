"""
Pydantic data models — shared between provider adapters, storage, and API layer.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────


class ProviderKind(str, Enum):
    """Distinguishes official API providers from CLI/subscription tools."""
    API = "api"          # Pure REST API with keys (OpenAI, Anthropic, Gemini, Mistral, OpenRouter)
    TOOL = "tool"        # Coding assistant / subscription tool (Claude Code, Codex, Gemini CLI, Mistral Vibe)


class DataSource(str, Enum):
    """Transparency: where does this data come from?"""
    OFFICIAL = "official"             # Documented, public API endpoint
    INFERRED = "inferred"             # Estimated from partial data (e.g. cost from token counts)
    EXPERIMENTAL = "experimental"     # Community-discovered / reverse-engineered endpoint
    UNAVAILABLE = "unavailable"       # Key not configured or endpoint returned an error


class MetricKind(str, Enum):
    COST_USD = "cost_usd"
    TOKENS_INPUT = "tokens_input"
    TOKENS_OUTPUT = "tokens_output"
    REQUESTS = "requests"
    CREDITS_USED = "credits_used"
    CREDITS_REMAINING = "credits_remaining"
    RATE_LIMIT_USED = "rate_limit_used"
    RATE_LIMIT_TOTAL = "rate_limit_total"


# ── Normalized metric point ────────────────────────────────────────────────────


class MetricPoint(BaseModel):
    """A single normalized measurement from a provider."""
    provider: str
    model: str | None = None
    kind: MetricKind
    value: float
    unit: str                        # e.g. "USD", "tokens", "requests"
    source: DataSource = DataSource.OFFICIAL
    period_start: datetime | None = None
    period_end: datetime | None = None
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None


# ── Provider status ────────────────────────────────────────────────────────────


class ProviderStatus(BaseModel):
    """Current health/status of a single provider adapter."""
    id: str                          # slug, e.g. "openai"
    display_name: str
    kind: ProviderKind
    configured: bool                 # API key / credentials available
    reachable: bool | None = None    # Last HTTP check result
    last_checked: datetime | None = None
    error: str | None = None
    data_source: DataSource = DataSource.UNAVAILABLE


# ── Timeseries entry ──────────────────────────────────────────────────────────


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    provider: str
    kind: MetricKind
    value: float


# ── Refresh run ───────────────────────────────────────────────────────────────


class RefreshRun(BaseModel):
    id: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    triggered_by: str = "scheduler"  # "scheduler" | "manual"
    providers_attempted: list[str] = Field(default_factory=list)
    providers_succeeded: list[str] = Field(default_factory=list)
    error: str | None = None


# ── Endpoint test result ──────────────────────────────────────────────────────


class EndpointTestResult(BaseModel):
    provider: str
    endpoint: str
    method: str = "GET"
    status_code: int | None = None
    ok: bool = False
    latency_ms: float | None = None
    notes: str | None = None
    is_experimental: bool = False
    tested_at: datetime = Field(default_factory=datetime.utcnow)


# ── API response shapes ────────────────────────────────────────────────────────


class OverviewResponse(BaseModel):
    total_cost_usd: float | None
    total_tokens: int | None
    total_requests: int | None
    active_providers: int
    configured_providers: int
    last_refresh: datetime | None
    next_refresh: datetime | None
    data_sources: dict[str, DataSource]


class ProviderCard(BaseModel):
    status: ProviderStatus
    metrics: list[MetricPoint]
    window_reset: datetime | None = None


class ModelBreakdown(BaseModel):
    model: str
    provider: str
    cost_usd: float | None
    tokens_input: int | None
    tokens_output: int | None
    requests: int | None


class UsageWindow(BaseModel):
    provider: str
    window_label: str        # e.g. "Monthly — May 2025"
    reset_at: datetime | None
    used: float | None
    limit: float | None
    unit: str
    percent_used: float | None
    source: DataSource


class RefreshStatus(BaseModel):
    last_run: RefreshRun | None
    next_run_at: datetime | None
    interval_minutes: int
