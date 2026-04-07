"""
Metrics aggregation service — computes KPIs, breakdowns, and window summaries
from normalized metric points stored in SQLite.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any

from app import db
from app.models import (
    DataSource,
    MetricKind,
    MetricPoint,
    ModelBreakdown,
    OverviewResponse,
    ProviderCard,
    ProviderStatus,
    UsageWindow,
)
from app.services.collector import ALL_PROVIDERS


async def get_overview(next_refresh: datetime | None = None) -> OverviewResponse:
    """Compute top-level KPIs."""
    metrics = await db.get_latest_metrics()
    last_run = await db.get_last_refresh_run()

    api_providers = [p for p in ALL_PROVIDERS if p.kind.value == "api"]
    configured = sum(1 for p in api_providers if p.configured)
    active = sum(1 for p in api_providers if p.configured)

    # Aggregate cost
    total_cost: float | None = None
    total_tokens: int | None = None
    total_requests: int | None = None
    data_sources: dict[str, DataSource] = {}

    for m in metrics:
        if m.kind == MetricKind.COST_USD and m.model is None:
            if m.source != DataSource.UNAVAILABLE and m.unit == "USD":
                total_cost = (total_cost or 0.0) + m.value
                data_sources[f"{m.provider}.cost"] = m.source

        if m.kind == MetricKind.TOKENS_INPUT and m.model is None:
            if m.source != DataSource.UNAVAILABLE:
                total_tokens = (total_tokens or 0) + int(m.value)
                data_sources[f"{m.provider}.tokens"] = m.source

        if m.kind == MetricKind.TOKENS_OUTPUT and m.model is None:
            if m.source != DataSource.UNAVAILABLE:
                total_tokens = (total_tokens or 0) + int(m.value)
                data_sources[f"{m.provider}.tokens"] = m.source

        if m.kind == MetricKind.REQUESTS and m.model is None:
            if m.source != DataSource.UNAVAILABLE:
                total_requests = (total_requests or 0) + int(m.value)
                data_sources[f"{m.provider}.requests"] = m.source

    return OverviewResponse(
        total_cost_usd=round(total_cost, 4) if total_cost is not None else None,
        total_tokens=total_tokens,
        total_requests=total_requests,
        active_providers=active,
        configured_providers=configured,
        last_refresh=last_run.started_at if last_run else None,
        next_refresh=next_refresh,
        data_sources=data_sources,
    )


async def get_provider_cards() -> list[ProviderCard]:
    """Build per-provider summary cards."""
    metrics = await db.get_latest_metrics()

    by_provider: dict[str, list[MetricPoint]] = {}
    for m in metrics:
        by_provider.setdefault(m.provider, []).append(m)

    cards: list[ProviderCard] = []
    for provider in ALL_PROVIDERS:
        if not provider.configured:
            continue
        pmetrics = by_provider.get(provider.id, [])
        cards.append(ProviderCard(
            status=provider.status(),
            metrics=pmetrics,
        ))

    return cards


async def get_model_breakdown() -> list[ModelBreakdown]:
    """Per-model aggregated metrics."""
    metrics = await db.get_latest_metrics()

    # Only model-level metrics (model is not None)
    by_model: dict[tuple[str, str], dict] = {}
    for m in metrics:
        if m.model is None:
            continue
        if m.source == DataSource.UNAVAILABLE:
            continue
        key = (m.provider, m.model)
        if key not in by_model:
            by_model[key] = {"cost": None, "input": None, "output": None, "requests": None}

        if m.kind == MetricKind.COST_USD:
            by_model[key]["cost"] = (by_model[key]["cost"] or 0.0) + m.value
        elif m.kind == MetricKind.TOKENS_INPUT:
            by_model[key]["input"] = (by_model[key]["input"] or 0) + int(m.value)
        elif m.kind == MetricKind.TOKENS_OUTPUT:
            by_model[key]["output"] = (by_model[key]["output"] or 0) + int(m.value)
        elif m.kind == MetricKind.REQUESTS:
            by_model[key]["requests"] = (by_model[key]["requests"] or 0) + int(m.value)

    result = []
    for (provider, model), vals in sorted(by_model.items()):
        result.append(ModelBreakdown(
            model=model,
            provider=provider,
            cost_usd=round(vals["cost"], 4) if vals["cost"] is not None else None,
            tokens_input=vals["input"],
            tokens_output=vals["output"],
            requests=vals["requests"],
        ))

    return sorted(result, key=lambda x: x.cost_usd or 0, reverse=True)


async def get_windows() -> list[UsageWindow]:
    """Usage window summaries (monthly resets, credit limits, etc.)"""
    metrics = await db.get_latest_metrics()

    now = datetime.utcnow()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_num = calendar.monthrange(now.year, now.month)[1]
    reset_at = first_day.replace(month=now.month % 12 + 1, day=1) if now.month < 12 else \
               first_day.replace(year=now.year + 1, month=1, day=1)

    windows: list[UsageWindow] = []

    # Build a lookup
    by_provider: dict[str, list[MetricPoint]] = {}
    for m in metrics:
        by_provider.setdefault(m.provider, []).append(m)

    for provider_id, pmetrics in by_provider.items():
        cost = next((m for m in pmetrics if m.kind == MetricKind.COST_USD and m.model is None), None)
        credits_remaining = next((m for m in pmetrics if m.kind == MetricKind.CREDITS_REMAINING), None)
        credits_used = next((m for m in pmetrics if m.kind == MetricKind.CREDITS_USED), None)
        rate_total = next((m for m in pmetrics if m.kind == MetricKind.RATE_LIMIT_TOTAL), None)

        # Cost/spend window (monthly)
        if cost and cost.source != DataSource.UNAVAILABLE:
            limit_metric = rate_total if rate_total and rate_total.unit == cost.unit else None
            windows.append(UsageWindow(
                provider=provider_id,
                window_label=f"Monthly — {now.strftime('%B %Y')}",
                reset_at=reset_at,
                used=cost.value,
                limit=limit_metric.value if limit_metric else None,
                unit=cost.unit,
                percent_used=(
                    (cost.value / limit_metric.value * 100) if limit_metric and limit_metric.value else None
                ),
                source=cost.source,
            ))

        # Credit balance window
        if credits_remaining:
            windows.append(UsageWindow(
                provider=provider_id,
                window_label="Credit Balance",
                reset_at=None,
                used=credits_used.value if credits_used else None,
                limit=None,
                unit=credits_remaining.unit,
                percent_used=None,
                source=credits_remaining.source,
            ))

    return windows
