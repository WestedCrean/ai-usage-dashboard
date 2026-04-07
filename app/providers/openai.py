"""
OpenAI provider adapter.

Official usage endpoint: GET /v1/usage  (requires org-level API key)
Billing/costs endpoint:  GET /dashboard/billing/usage  (official, same key)

Data source: OFFICIAL for token counts; cost is INFERRED if only tokens are available.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind
from app.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    id = "openai"
    display_name = "OpenAI"
    kind = ProviderKind.API
    base_url = "https://api.openai.com"

    # Official usage dashboard endpoint (organization-level)
    _USAGE_URL = "https://api.openai.com/v1/usage"
    # Billing credit grants / subscription info
    _BILLING_URL = "https://api.openai.com/dashboard/billing/usage"

    def _check_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    def _headers(self) -> dict[str, str]:
        settings = get_settings()
        h = {"Authorization": f"Bearer {settings.openai_api_key}"}
        if settings.openai_org_id:
            h["OpenAI-Organization"] = settings.openai_org_id
        return h

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        if not self._configured:
            return [], None

        now = datetime.utcnow()
        month_start = date(now.year, now.month, 1)
        month_end = date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

        metrics: list[MetricPoint] = []
        raw: dict[str, Any] = {}

        # ── Usage (tokens / requests per model) ────────────────────────────
        try:
            resp = await client.get(
                self._USAGE_URL,
                headers=self._headers(),
                params={
                    "date": month_start.strftime("%Y-%m-%d"),
                    "end_date": month_end.strftime("%Y-%m-%d"),
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["usage"] = data

            # Aggregate across models
            total_input = 0
            total_output = 0
            total_requests = 0
            by_model: dict[str, dict] = {}

            for day_data in data.get("data", []):
                for snap in day_data.get("aggregation_timestamp", []) if isinstance(day_data, dict) else []:
                    pass

            # Flatten daily data
            for entry in data.get("data", []):
                for model_entry in entry if isinstance(entry, list) else [entry]:
                    if not isinstance(model_entry, dict):
                        continue
                    model = model_entry.get("snapshot_id") or model_entry.get("model", "unknown")
                    n_ctx = model_entry.get("n_context_tokens_total", 0) or 0
                    n_gen = model_entry.get("n_generated_tokens_total", 0) or 0
                    n_req = model_entry.get("n_requests", 0) or 0

                    total_input += n_ctx
                    total_output += n_gen
                    total_requests += n_req

                    if model not in by_model:
                        by_model[model] = {"input": 0, "output": 0, "requests": 0}
                    by_model[model]["input"] += n_ctx
                    by_model[model]["output"] += n_gen
                    by_model[model]["requests"] += n_req

            if total_input or total_output:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.TOKENS_INPUT,
                    value=float(total_input),
                    unit="tokens",
                    source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    period_end=datetime.combine(month_end, datetime.max.time()),
                    notes="MTD via /v1/usage",
                ))
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.TOKENS_OUTPUT,
                    value=float(total_output),
                    unit="tokens",
                    source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    period_end=datetime.combine(month_end, datetime.max.time()),
                    notes="MTD via /v1/usage",
                ))

            if total_requests:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.REQUESTS,
                    value=float(total_requests),
                    unit="requests",
                    source=DataSource.OFFICIAL,
                    notes="MTD via /v1/usage",
                ))

            # Per-model breakdown
            for model, vals in by_model.items():
                if vals["input"]:
                    metrics.append(MetricPoint(
                        provider=self.id,
                        model=model,
                        kind=MetricKind.TOKENS_INPUT,
                        value=float(vals["input"]),
                        unit="tokens",
                        source=DataSource.OFFICIAL,
                    ))
                if vals["output"]:
                    metrics.append(MetricPoint(
                        provider=self.id,
                        model=model,
                        kind=MetricKind.TOKENS_OUTPUT,
                        value=float(vals["output"]),
                        unit="tokens",
                        source=DataSource.OFFICIAL,
                    ))

        except httpx.HTTPStatusError as exc:
            raw["usage_error"] = str(exc)
        except Exception as exc:
            raw["usage_error"] = str(exc)

        # ── Billing / cost ─────────────────────────────────────────────────
        try:
            resp = await client.get(
                self._BILLING_URL,
                headers=self._headers(),
                params={
                    "start_date": month_start.strftime("%Y-%m-%d"),
                    "end_date": (month_end + timedelta(days=1)).strftime("%Y-%m-%d"),
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            billing = resp.json()
            raw["billing"] = billing

            total_cost = billing.get("total_usage", 0) or 0  # in cents
            if total_cost:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.COST_USD,
                    value=round(total_cost / 100, 4),
                    unit="USD",
                    source=DataSource.OFFICIAL,
                    period_start=datetime.combine(month_start, datetime.min.time()),
                    period_end=datetime.combine(month_end, datetime.max.time()),
                    notes="MTD via /dashboard/billing/usage (in cents, converted)",
                ))

        except httpx.HTTPStatusError as exc:
            raw["billing_error"] = str(exc)
        except Exception as exc:
            raw["billing_error"] = str(exc)

        return metrics, raw
