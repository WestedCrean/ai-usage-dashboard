from datetime import datetime

import pytest

from app.models import DataSource, MetricKind, MetricPoint
from app.services import metrics


async def _fake_latest_metrics():
    now = datetime.utcnow()
    return [
        MetricPoint(
            provider="openrouter",
            kind=MetricKind.COST_USD,
            value=20,
            unit="USD",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="openrouter",
            kind=MetricKind.RATE_LIMIT_TOTAL,
            value=100,
            unit="USD",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="mistral",
            kind=MetricKind.CREDITS_USED,
            value=8,
            unit="EUR",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="mistral",
            kind=MetricKind.CREDITS_REMAINING,
            value=42,
            unit="EUR",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
        MetricPoint(
            provider="mistral",
            kind=MetricKind.RATE_LIMIT_TOTAL,
            value=100,
            unit="USD",
            source=DataSource.OFFICIAL,
            captured_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_windows_only_uses_matching_units_for_limits(monkeypatch):
    monkeypatch.setattr(metrics.db, "get_latest_metrics", _fake_latest_metrics)

    windows = await metrics.get_windows()
    by_provider = {w.provider + ':' + w.window_label: w for w in windows}

    openrouter = by_provider["openrouter:Monthly — " + datetime.utcnow().strftime('%B %Y')]
    assert openrouter.limit == 100
    assert round(openrouter.percent_used, 2) == 20.0

    mistral_balance = by_provider["mistral:Credit Balance"]
    assert mistral_balance.unit == "EUR"

    assert all(not (w.provider == "mistral" and w.window_label.startswith("Monthly")) for w in windows)
