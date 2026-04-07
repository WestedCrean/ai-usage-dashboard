"""Tests for provider filtering — unconfigured providers should not appear in cards or windows."""

from datetime import datetime

import pytest

from app.models import DataSource, MetricKind, MetricPoint
from app.services import metrics


class DummyProvider:
    def __init__(self, id: str, configured: bool, kind: str = "api"):
        self.id = id
        self.configured = configured
        self.kind = type("Kind", (), {"value": kind})()

    def status(self):
        from app.models import ProviderStatus, ProviderKind, DataSource
        return ProviderStatus(
            id=self.id,
            display_name=self.id.title(),
            kind=ProviderKind.API if self.kind.value == "api" else ProviderKind.TOOL,
            configured=self.configured,
            data_source=DataSource.OFFICIAL if self.configured else DataSource.UNAVAILABLE,
        )


async def _fake_latest_metrics():
    now = datetime.utcnow()
    return [
        MetricPoint(
            provider="openai",
            kind=MetricKind.COST_USD,
            value=10.0,
            unit="USD",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="unconfigured_tool",
            kind=MetricKind.COST_USD,
            value=0.0,
            unit="USD",
            source=DataSource.UNAVAILABLE,
            captured_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_provider_cards_exclude_unconfigured(monkeypatch):
    monkeypatch.setattr(metrics.db, "get_latest_metrics", _fake_latest_metrics)
    monkeypatch.setattr(
        metrics,
        "ALL_PROVIDERS",
        [
            DummyProvider("openai", configured=True),
            DummyProvider("unconfigured_tool", configured=False, kind="tool"),
        ],
    )

    cards = await metrics.get_provider_cards()
    ids = [c.status.id for c in cards]
    assert "openai" in ids
    assert "unconfigured_tool" not in ids


@pytest.mark.asyncio
async def test_provider_cards_all_unconfigured_returns_empty(monkeypatch):
    monkeypatch.setattr(metrics.db, "get_latest_metrics", _fake_latest_metrics)
    monkeypatch.setattr(
        metrics,
        "ALL_PROVIDERS",
        [
            DummyProvider("openai", configured=False),
            DummyProvider("unconfigured_tool", configured=False, kind="tool"),
        ],
    )

    cards = await metrics.get_provider_cards()
    assert cards == []


@pytest.mark.asyncio
async def test_windows_exclude_unconfigured_providers(monkeypatch):
    now = datetime.utcnow()

    async def _metrics():
        return [
            MetricPoint(
                provider="openai",
                kind=MetricKind.COST_USD,
                value=5.0,
                unit="USD",
                source=DataSource.OFFICIAL,
                captured_at=now,
            ),
            MetricPoint(
                provider="unconfigured_tool",
                kind=MetricKind.COST_USD,
                value=0.0,
                unit="USD",
                source=DataSource.UNAVAILABLE,
                captured_at=now,
            ),
        ]

    monkeypatch.setattr(metrics.db, "get_latest_metrics", _metrics)
    monkeypatch.setattr(
        metrics,
        "ALL_PROVIDERS",
        [
            DummyProvider("openai", configured=True),
            DummyProvider("unconfigured_tool", configured=False, kind="tool"),
        ],
    )

    windows = await metrics.get_windows()
    providers_in_windows = {w.provider for w in windows}
    assert "unconfigured_tool" not in providers_in_windows
