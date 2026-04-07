"""
Mistral AI provider adapter.

Official usage endpoint: GET /v1/organization/billing/summary  (workspace-level)
Also: GET /v1/organization/usage  (detailed token usage)

Data source: OFFICIAL
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind
from app.providers.base import BaseProvider


class MistralProvider(BaseProvider):
    id = "mistral"
    display_name = "Mistral AI"
    kind = ProviderKind.API
    base_url = "https://api.mistral.ai"

    _BILLING_URL = "https://api.mistral.ai/v1/organization/billing/summary"
    _USAGE_URL = "https://api.mistral.ai/v1/organization/usage"

    def _check_configured(self) -> bool:
        return bool(get_settings().mistral_api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {get_settings().mistral_api_key}"}

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        if not self._configured:
            return [], None

        now = datetime.utcnow()
        month_start = date(now.year, now.month, 1)
        month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

        metrics: list[MetricPoint] = []
        raw: dict[str, Any] = {}

        # ── Billing summary ────────────────────────────────────────────────
        try:
            resp = await client.get(
                self._BILLING_URL,
                headers=self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            billing = resp.json()
            raw["billing"] = billing

            # Balance / credits
            balance = billing.get("balance")
            if balance is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.CREDITS_REMAINING,
                    value=float(balance),
                    unit="EUR",
                    source=DataSource.OFFICIAL,
                    notes="Account balance via /v1/organization/billing/summary",
                ))

        except httpx.HTTPStatusError as exc:
            raw["billing_error"] = f"{exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            raw["billing_error"] = str(exc)

        # ── Usage detail ───────────────────────────────────────────────────
        try:
            resp = await client.get(
                self._USAGE_URL,
                headers=self._headers(),
                params={
                    "start_date": month_start.strftime("%Y-%m-%d"),
                    "end_date": month_end.strftime("%Y-%m-%d"),
                    "page_size": 100,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            usage = resp.json()
            raw["usage"] = usage

            total_in = 0
            total_out = 0
            total_cost = 0.0
            by_model: dict[str, dict] = {}

            for entry in usage.get("data", []):
                model = entry.get("model", "unknown")
                inp = entry.get("input_tokens", 0) or 0
                out = entry.get("output_tokens", 0) or 0
                cost = entry.get("cost_eur", 0.0) or 0.0

                total_in += inp
                total_out += out
                total_cost += cost

                if model not in by_model:
                    by_model[model] = {"input": 0, "output": 0, "cost": 0.0}
                by_model[model]["input"] += inp
                by_model[model]["output"] += out
                by_model[model]["cost"] += cost

            for model, vals in by_model.items():
                if vals["input"]:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_INPUT, value=float(vals["input"]),
                        unit="tokens", source=DataSource.OFFICIAL,
                    ))
                if vals["output"]:
                    metrics.append(MetricPoint(
                        provider=self.id, model=model,
                        kind=MetricKind.TOKENS_OUTPUT, value=float(vals["output"]),
                        unit="tokens", source=DataSource.OFFICIAL,
                    ))

            if total_in:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.TOKENS_INPUT,
                    value=float(total_in), unit="tokens", source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    notes="MTD via /v1/organization/usage",
                ))
            if total_out:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.TOKENS_OUTPUT,
                    value=float(total_out), unit="tokens", source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    notes="MTD via /v1/organization/usage",
                ))
            if total_cost:
                metrics.append(MetricPoint(
                    provider=self.id, kind=MetricKind.CREDITS_USED,
                    value=round(total_cost, 4), unit="EUR",
                    source=DataSource.OFFICIAL,
                    notes="MTD spend in EUR via /v1/organization/usage",
                ))

        except httpx.HTTPStatusError as exc:
            raw["usage_error"] = f"{exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            raw["usage_error"] = str(exc)

        return metrics, raw
