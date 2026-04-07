"""
OpenRouter provider adapter.

Official endpoints:
  GET /api/v1/auth/key          — key info, credit balance
  GET /api/v1/generation        — recent generation details (last N requests)

Data source: OFFICIAL
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind
from app.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    id = "openrouter"
    display_name = "OpenRouter"
    kind = ProviderKind.API
    base_url = "https://openrouter.ai"

    _KEY_URL = "https://openrouter.ai/api/v1/auth/key"
    _GENERATION_URL = "https://openrouter.ai/api/v1/generation"

    def _check_configured(self) -> bool:
        return bool(get_settings().openrouter_api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {get_settings().openrouter_api_key}"}

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        if not self._configured:
            return [], None

        metrics: list[MetricPoint] = []
        raw: dict[str, Any] = {}

        # ── Key/credit info ────────────────────────────────────────────────
        try:
            resp = await client.get(self._KEY_URL, headers=self._headers(), timeout=10.0)
            resp.raise_for_status()
            key_data = resp.json().get("data", {})
            raw["key"] = key_data

            usage_cents = key_data.get("usage", 0) or 0        # credits used (in USD)
            limit = key_data.get("limit")                       # credit limit, None = unlimited
            limit_remaining = key_data.get("limit_remaining")

            if usage_cents is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.CREDITS_USED,
                    value=float(usage_cents),
                    unit="USD",
                    source=DataSource.OFFICIAL,
                    notes="Credit usage via /api/v1/auth/key",
                ))
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.COST_USD,
                    value=float(usage_cents),
                    unit="USD",
                    source=DataSource.OFFICIAL,
                    notes="Total credit spend via /api/v1/auth/key",
                ))

            if limit is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.RATE_LIMIT_TOTAL,
                    value=float(limit),
                    unit="USD",
                    source=DataSource.OFFICIAL,
                    notes="Credit limit",
                ))

            if limit_remaining is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.CREDITS_REMAINING,
                    value=float(limit_remaining),
                    unit="USD",
                    source=DataSource.OFFICIAL,
                ))

        except httpx.HTTPStatusError as exc:
            raw["key_error"] = f"{exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            raw["key_error"] = str(exc)

        # ── Recent generations (token breakdown) ───────────────────────────
        try:
            resp = await client.get(
                self._GENERATION_URL,
                headers=self._headers(),
                params={"limit": 200},
                timeout=15.0,
            )
            resp.raise_for_status()
            gen_data = resp.json()
            raw["generations"] = gen_data

            total_in = 0
            total_out = 0
            by_model: dict[str, dict] = {}

            for entry in gen_data.get("data", []):
                model = entry.get("model", "unknown")
                inp = entry.get("tokens_prompt", 0) or 0
                out = entry.get("tokens_completion", 0) or 0

                total_in += inp
                total_out += out

                if model not in by_model:
                    by_model[model] = {"input": 0, "output": 0}
                by_model[model]["input"] += inp
                by_model[model]["output"] += out

            for model, vals in by_model.items():
                if vals["input"]:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_INPUT, value=float(vals["input"]),
                        unit="tokens", source=DataSource.OFFICIAL,
                        notes="Recent 200 requests",
                    ))
                if vals["output"]:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_OUTPUT, value=float(vals["output"]),
                        unit="tokens", source=DataSource.OFFICIAL,
                        notes="Recent 200 requests",
                    ))

        except httpx.HTTPStatusError as exc:
            raw["generations_error"] = f"{exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            raw["generations_error"] = str(exc)

        return metrics, raw
