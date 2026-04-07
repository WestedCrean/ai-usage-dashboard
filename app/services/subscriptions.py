"""
Subscription usage + savings aggregation.

Computes per-tool usage vs limit and estimates savings compared to direct API pricing
for Claude Code, OpenAI Codex, and Mistral Vibe.
"""

from __future__ import annotations

import calendar
from datetime import datetime
from typing import Any

from app import db
from app.config import get_settings
from app.models import (
    DataSource,
    MetricKind,
    MetricPoint,
    SubscriptionSummaryResponse,
    SubscriptionToolUsage,
)

# Mapping: tool_id -> config attribute names
_TOOL_CONFIG = {
    "claude_code": {
        "display_name": "Claude Code",
        "price_attr": "claude_code_subscription_price",
        "plan_attr": "claude_code_plan_name",
        "cost_per_1k_attr": "claude_api_cost_per_1k_tokens",
    },
    "codex": {
        "display_name": "OpenAI Codex",
        "price_attr": "codex_subscription_price",
        "plan_attr": "codex_plan_name",
        "cost_per_1k_attr": "openai_api_cost_per_1k_tokens",
    },
    "mistral_vibe": {
        "display_name": "Mistral Vibe",
        "price_attr": "mistral_vibe_subscription_price",
        "plan_attr": "mistral_vibe_plan_name",
        "cost_per_1k_attr": "mistral_api_cost_per_1k_tokens",
    },
}

SUPPORTED_TOOL_IDS = list(_TOOL_CONFIG.keys())


def _estimate_api_cost(tokens: float, cost_per_1k: float) -> float:
    """Estimate what *tokens* would cost at *cost_per_1k* USD per 1 000 tokens."""
    return round(tokens / 1000.0 * cost_per_1k, 4)


async def get_subscription_summary() -> SubscriptionSummaryResponse:
    """Build the subscription usage + savings summary for all three tools."""
    settings = get_settings()
    metrics = await db.get_latest_metrics()

    now = datetime.utcnow()
    window_label = f"Monthly — {now.strftime('%B %Y')}"
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    reset_at = (
        first_day.replace(month=now.month % 12 + 1, day=1)
        if now.month < 12
        else first_day.replace(year=now.year + 1, month=1, day=1)
    )

    # Group metrics by provider
    by_provider: dict[str, list[MetricPoint]] = {}
    for m in metrics:
        by_provider.setdefault(m.provider, []).append(m)

    tools: list[SubscriptionToolUsage] = []
    caveats: list[str] = []

    for tool_id, cfg in _TOOL_CONFIG.items():
        sub_price = getattr(settings, cfg["price_attr"])
        plan_name = getattr(settings, cfg["plan_attr"])
        cost_per_1k = getattr(settings, cfg["cost_per_1k_attr"])

        pmetrics = by_provider.get(tool_id, [])

        # Try to find token metrics (experimental or official)
        tok_in = next(
            (m for m in pmetrics if m.kind == MetricKind.TOKENS_INPUT and m.source != DataSource.UNAVAILABLE),
            None,
        )
        tok_out = next(
            (m for m in pmetrics if m.kind == MetricKind.TOKENS_OUTPUT and m.source != DataSource.UNAVAILABLE),
            None,
        )
        cost_metric = next(
            (m for m in pmetrics if m.kind == MetricKind.COST_USD and m.source != DataSource.UNAVAILABLE),
            None,
        )
        rate_used = next(
            (m for m in pmetrics if m.kind == MetricKind.RATE_LIMIT_USED and m.source != DataSource.UNAVAILABLE),
            None,
        )
        rate_total = next(
            (m for m in pmetrics if m.kind == MetricKind.RATE_LIMIT_TOTAL and m.source != DataSource.UNAVAILABLE),
            None,
        )

        total_tokens = None
        if tok_in or tok_out:
            total_tokens = (tok_in.value if tok_in else 0.0) + (tok_out.value if tok_out else 0.0)

        # Determine source classification
        sources = [m.source for m in pmetrics if m.source != DataSource.UNAVAILABLE]
        source = DataSource.UNAVAILABLE
        if DataSource.OFFICIAL in sources:
            source = DataSource.OFFICIAL
        elif DataSource.EXPERIMENTAL in sources:
            source = DataSource.EXPERIMENTAL
        elif DataSource.INFERRED in sources:
            source = DataSource.INFERRED

        # used/limit — prefer rate-limit metrics, fall back to cost
        used = None
        limit = None
        unit = "USD"
        if rate_used is not None:
            used = rate_used.value
            unit = rate_used.unit
        elif cost_metric is not None:
            used = cost_metric.value
            unit = cost_metric.unit

        if rate_total is not None:
            limit = rate_total.value

        percent_used = None
        if used is not None and limit is not None and limit > 0:
            percent_used = round(used / limit * 100, 2)

        # API equivalent cost estimate
        api_equiv: float | None = None
        notes_parts: list[str] = []

        if total_tokens is not None and total_tokens > 0:
            api_equiv = _estimate_api_cost(total_tokens, cost_per_1k)
            notes_parts.append(
                f"API cost estimated from {int(total_tokens)} tokens "
                f"× ${cost_per_1k}/1K (configurable via env)."
            )
        elif cost_metric is not None and cost_metric.source != DataSource.UNAVAILABLE:
            # If we have a direct cost metric but no tokens, use the cost as the API equivalent
            api_equiv = round(cost_metric.value, 4)
            notes_parts.append("API equivalent derived from reported cost metric.")
        else:
            notes_parts.append(
                "No usage data available for this tool. "
                "Savings estimate requires token or cost metrics."
            )

        # Savings
        savings: float | None = None
        if api_equiv is not None and sub_price > 0:
            savings = round(max(api_equiv - sub_price, 0), 4)
        elif api_equiv is not None and sub_price == 0:
            notes_parts.append("Subscription price not configured; savings not computed.")

        if source == DataSource.UNAVAILABLE:
            notes_parts.insert(
                0,
                f"{cfg['display_name']} does not expose a public usage API. "
                "Data shown is placeholder / config-driven.",
            )

        tools.append(
            SubscriptionToolUsage(
                tool_id=tool_id,
                display_name=cfg["display_name"],
                plan_name=plan_name if sub_price > 0 else None,
                window_label=window_label,
                used=used,
                limit=limit,
                unit=unit,
                percent_used=percent_used,
                reset_at=reset_at,
                source=source,
                api_equivalent_cost=api_equiv,
                subscription_price=sub_price if sub_price > 0 else None,
                estimated_savings=savings,
                notes=" ".join(notes_parts) if notes_parts else None,
            )
        )

    # Totals
    total_sub = sum(t.subscription_price for t in tools if t.subscription_price is not None)
    total_api = sum(t.api_equivalent_cost for t in tools if t.api_equivalent_cost is not None)
    total_savings = sum(t.estimated_savings for t in tools if t.estimated_savings is not None)

    # Global caveats
    caveats.append(
        "Subscription prices and per-token API costs are config-driven defaults. "
        "Override via environment variables for accuracy."
    )
    if any(t.source == DataSource.UNAVAILABLE for t in tools):
        caveats.append(
            "One or more tools lack a public usage API. Savings estimates for those tools "
            "require experimental data (ENABLE_EXPERIMENTAL=true) or manual input."
        )

    return SubscriptionSummaryResponse(
        tools=tools,
        total_subscription_cost=round(total_sub, 2) if total_sub else None,
        total_api_equivalent=round(total_api, 4) if total_api else None,
        total_estimated_savings=round(total_savings, 4) if total_savings else None,
        generated_at=now,
        caveats=caveats,
    )
