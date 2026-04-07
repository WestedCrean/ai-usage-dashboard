from datetime import datetime

import pytest

from app.models import DataSource, MetricKind, MetricPoint
from app.services import metrics


class DummyProvider:
    def __init__(self, configured: bool, kind: str = "api"):
        self.configured = configured
        self.kind = type("Kind", (), {"value": kind})()


async def _fake_last_run():
    return None


async def _fake_latest_metrics():
    now = datetime.utcnow()
    return [
        MetricPoint(
            provider="openai",
            kind=MetricKind.COST_USD,
            value=12.5,
            unit="USD",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="mistral",
            kind=MetricKind.CREDITS_USED,
            value=8.0,
            unit="EUR",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="openai",
            kind=MetricKind.TOKENS_INPUT,
            value=100,
            unit="tokens",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="openai",
            kind=MetricKind.TOKENS_OUTPUT,
            value=50,
            unit="tokens",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="openai",
            kind=MetricKind.REQUESTS,
            value=7,
            unit="requests",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_overview_excludes_non_usd_costs(monkeypatch):
    monkeypatch.setattr(metrics.db, "get_latest_metrics", _fake_latest_metrics)
    monkeypatch.setattr(metrics.db, "get_last_refresh_run", _fake_last_run)
    monkeypatch.setattr(
        metrics,
        "ALL_PROVIDERS",
        [DummyProvider(True), DummyProvider(False), DummyProvider(True, kind="tool")],
    )

    overview = await metrics.get_overview()

    assert overview.total_cost_usd == 12.5
    assert overview.total_tokens == 150
    assert overview.total_requests == 7
    assert overview.configured_providers == 1
    assert overview.data_sources["openai.cost"] == DataSource.OFFICIAL
    assert overview.data_sources["openai.tokens"] == DataSource.OFFICIAL
    assert overview.data_sources["openai.requests"] == DataSource.OFFICIAL
