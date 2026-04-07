"""
Anthropic provider adapter.

Official usage endpoint: GET /v1/usage  (Beta — requires Authorization header)
Token cost endpoint: billing is typically accessed via the Console; API is limited.

Data source: OFFICIAL for token usage; cost is INFERRED if billing API is unavailable.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind
from app.providers.base import BaseProvider


# Rough pricing (USD per 1M tokens) — used for cost inference when billing API unavailable
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4":        (15.0, 75.0),
    "claude-sonnet-4-5":    (3.0, 15.0),
    "claude-3-7-sonnet":    (3.0, 15.0),
    "claude-3-5-haiku":     (0.8, 4.0),
    "claude-3-haiku":       (0.25, 1.25),
    "claude-3-opus":        (15.0, 75.0),
    "claude-3-sonnet":      (3.0, 15.0),
}


def _infer_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Infer cost from public pricing when billing API is not available."""
    for key, (input_price, output_price) in _MODEL_PRICES.items():
        if key in model.lower():
            return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return None


class AnthropicProvider(BaseProvider):
    id = "anthropic"
    display_name = "Anthropic"
    kind = ProviderKind.API
    base_url = "https://api.anthropic.com"

    _USAGE_URL = "https://api.anthropic.com/v1/usage"

    def _check_configured(self) -> bool:
        return bool(get_settings().anthropic_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": get_settings().anthropic_api_key or "",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "usage-2025-01-01",
        }

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        if not self._configured:
            return [], None

        now = datetime.utcnow()
        month_start = date(now.year, now.month, 1)
        month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

        metrics: list[MetricPoint] = []
        raw: dict[str, Any] = {}

        try:
            resp = await client.get(
                self._USAGE_URL,
                headers=self._headers(),
                params={
                    "start_time": f"{month_start.isoformat()}T00:00:00Z",
                    "end_time": f"{month_end.isoformat()}T23:59:59Z",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["usage"] = data

            # Aggregate
            total_input = 0
            total_output = 0
            total_requests = 0
            inferred_cost = 0.0
            cost_inferred = False

            for entry in data.get("data", []):
                model = entry.get("model", "unknown")
                inp = entry.get("input_tokens", 0) or 0
                out = entry.get("output_tokens", 0) or 0
                reqs = entry.get("requests", 0) or 0

                total_input += inp
                total_output += out
                total_requests += reqs

                # Per-model metrics
                if inp:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_INPUT, value=float(inp),
                        unit="tokens", source=DataSource.OFFICIAL,
                    ))
                if out:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_OUTPUT, value=float(out),
                        unit="tokens", source=DataSource.OFFICIAL,
                    ))

                cost = _infer_cost(model, inp, out)
                if cost is not None:
                    inferred_cost += cost
                    cost_inferred = True

            if total_input:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.TOKENS_INPUT,
                    value=float(total_input), unit="tokens",
                    source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    notes="MTD via /v1/usage (beta)",
                ))
            if total_output:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.TOKENS_OUTPUT,
                    value=float(total_output), unit="tokens",
                    source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    notes="MTD via /v1/usage (beta)",
                ))
            if total_requests:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.REQUESTS,
                    value=float(total_requests), unit="requests",
                    source=DataSource.OFFICIAL,
                ))
            if cost_inferred and inferred_cost > 0:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.COST_USD,
                    value=round(inferred_cost, 4), unit="USD",
                    source=DataSource.INFERRED,
                    notes="Inferred from public per-token pricing; not official billing data",
                ))

        except httpx.HTTPStatusError as exc:
            raw["usage_error"] = f"{exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            raw["usage_error"] = str(exc)

        return metrics, raw
