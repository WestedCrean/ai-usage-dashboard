"""Tests for subscription usage + savings aggregation."""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.models import DataSource, MetricKind, MetricPoint
from app.services import subscriptions


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_metric(provider, kind, value, unit="tokens", source=DataSource.OFFICIAL, model=None):
    return MetricPoint(
        provider=provider,
        model=model,
        kind=kind,
        value=value,
        unit=unit,
        source=source,
        captured_at=datetime.utcnow(),
    )


# ── Fake db returns ──────────────────────────────────────────────────────────

async def _empty_metrics():
    return []


async def _metrics_with_tokens():
    """Claude Code has experimental token data; others have nothing."""
    return [
        # Claude Code — experimental tokens
        _make_metric("claude_code", MetricKind.TOKENS_INPUT, 50000, source=DataSource.EXPERIMENTAL),
        _make_metric("claude_code", MetricKind.TOKENS_OUTPUT, 20000, source=DataSource.EXPERIMENTAL),
        # Claude Code — the default UNAVAILABLE cost placeholder emitted by tool_usage adapter
        _make_metric("claude_code", MetricKind.COST_USD, 0.0, unit="USD", source=DataSource.UNAVAILABLE),
        # Codex — only the UNAVAILABLE placeholder
        _make_metric("codex", MetricKind.COST_USD, 0.0, unit="USD", source=DataSource.UNAVAILABLE),
        # Mistral Vibe — only the UNAVAILABLE placeholder
        _make_metric("mistral_vibe", MetricKind.COST_USD, 0.0, unit="USD", source=DataSource.UNAVAILABLE),
    ]


async def _metrics_with_cost():
    """Codex has a direct cost metric (official)."""
    return [
        _make_metric("codex", MetricKind.COST_USD, 45.0, unit="USD", source=DataSource.OFFICIAL),
    ]


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_metrics_returns_all_tools(monkeypatch):
    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _empty_metrics)
    result = await subscriptions.get_subscription_summary()

    assert len(result.tools) == 3
    ids = {t.tool_id for t in result.tools}
    assert ids == {"claude_code", "codex", "mistral_vibe"}

    # All should be UNAVAILABLE with no savings
    for t in result.tools:
        assert t.source == DataSource.UNAVAILABLE
        assert t.api_equivalent_cost is None
        assert t.estimated_savings is None


@pytest.mark.asyncio
async def test_token_based_savings_estimation(monkeypatch):
    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _metrics_with_tokens)
    result = await subscriptions.get_subscription_summary()

    claude = next(t for t in result.tools if t.tool_id == "claude_code")

    # 70 000 tokens × $0.015/1K = $1.05
    assert claude.api_equivalent_cost == pytest.approx(1.05, abs=0.01)
    assert claude.subscription_price == 20.0
    # Savings = max(1.05 - 20.0, 0) = 0  (subscription costs more than API equiv)
    assert claude.estimated_savings == 0.0
    assert claude.source == DataSource.EXPERIMENTAL


@pytest.mark.asyncio
async def test_cost_metric_used_as_api_equivalent(monkeypatch):
    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _metrics_with_cost)
    result = await subscriptions.get_subscription_summary()

    codex = next(t for t in result.tools if t.tool_id == "codex")

    assert codex.api_equivalent_cost == 45.0
    # Savings = max(45.0 - 200.0, 0) = 0  (sub costs more)
    assert codex.estimated_savings == 0.0
    assert codex.source == DataSource.OFFICIAL


@pytest.mark.asyncio
async def test_savings_positive_when_api_exceeds_sub(monkeypatch):
    """When API equivalent exceeds subscription price, savings should be positive."""
    async def _expensive():
        return [
            _make_metric("claude_code", MetricKind.TOKENS_INPUT, 5_000_000, source=DataSource.EXPERIMENTAL),
        ]

    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _expensive)
    result = await subscriptions.get_subscription_summary()

    claude = next(t for t in result.tools if t.tool_id == "claude_code")

    # 5M tokens × $0.015/1K = $75.00
    assert claude.api_equivalent_cost == pytest.approx(75.0, abs=0.01)
    assert claude.subscription_price == 20.0
    assert claude.estimated_savings == pytest.approx(55.0, abs=0.01)

    # Total savings should reflect this
    assert result.total_estimated_savings is not None
    assert result.total_estimated_savings >= 55.0


@pytest.mark.asyncio
async def test_totals_computed_correctly(monkeypatch):
    """Totals should sum across tools."""
    async def _multi():
        return [
            _make_metric("claude_code", MetricKind.TOKENS_INPUT, 5_000_000, source=DataSource.EXPERIMENTAL),
            _make_metric("codex", MetricKind.COST_USD, 500.0, unit="USD", source=DataSource.OFFICIAL),
        ]

    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _multi)
    result = await subscriptions.get_subscription_summary()

    # total_subscription_cost = 20 + 200 + 19.99 = 239.99
    assert result.total_subscription_cost == pytest.approx(239.99, abs=0.01)

    # total_api_equivalent: Claude = 75.00, Codex = 500.00 → 575.00
    assert result.total_api_equivalent == pytest.approx(575.0, abs=0.01)


@pytest.mark.asyncio
async def test_caveats_always_present(monkeypatch):
    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _empty_metrics)
    result = await subscriptions.get_subscription_summary()

    assert len(result.caveats) >= 1
    assert any("config-driven" in c.lower() or "environment" in c.lower() for c in result.caveats)


@pytest.mark.asyncio
async def test_estimate_api_cost_helper():
    cost = subscriptions._estimate_api_cost(100_000, 0.01)
    # 100K tokens × $0.01/1K = $1.00
    assert cost == pytest.approx(1.0, abs=0.001)


@pytest.mark.asyncio
async def test_window_label_and_reset(monkeypatch):
    monkeypatch.setattr(subscriptions.db, "get_latest_metrics", _empty_metrics)
    result = await subscriptions.get_subscription_summary()

    now = datetime.utcnow()
    expected_label = f"Monthly — {now.strftime('%B %Y')}"
    for t in result.tools:
        assert t.window_label == expected_label
        assert t.reset_at is not None
