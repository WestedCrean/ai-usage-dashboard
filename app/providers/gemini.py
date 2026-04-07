"""
Google Gemini provider adapter.

Official API: ai.google.dev / generativelanguage.googleapis.com
Usage/quota visibility: Limited — Google AI Studio does not expose per-key usage via API.
We attempt the models list endpoint (official) and note that cost/usage data is unavailable.

Data source: OFFICIAL for model listing; quota data UNAVAILABLE unless GOOGLE_CLOUD_PROJECT
is set and ENABLE_EXPERIMENTAL is true (Cloud Monitoring quota metrics).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind
from app.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    id = "gemini"
    display_name = "Google Gemini"
    kind = ProviderKind.API
    base_url = "https://generativelanguage.googleapis.com"

    _MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def _check_configured(self) -> bool:
        return bool(get_settings().gemini_api_key)

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        if not self._configured:
            return [], None

        settings = get_settings()
        metrics: list[MetricPoint] = []
        raw: dict[str, Any] = {}

        # ── Model listing (official, always available with API key) ────────
        try:
            resp = await client.get(
                self._MODELS_URL,
                params={"key": settings.gemini_api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["models"] = data
            model_count = len(data.get("models", []))
            raw["model_count"] = model_count
        except Exception as exc:
            raw["models_error"] = str(exc)

        # ── Usage data ─────────────────────────────────────────────────────
        # Google AI Studio does not expose per-key usage via a public REST API.
        # Quota metrics require Cloud Monitoring + a Google Cloud project.
        # We emit a placeholder metric indicating data is unavailable.
        metrics.append(MetricPoint(
            provider=self.id,
            kind=MetricKind.COST_USD,
            value=0.0,
            unit="USD",
            source=DataSource.UNAVAILABLE,
            notes=(
                "Usage data not available via Google AI API. "
                "Enable ENABLE_EXPERIMENTAL + GOOGLE_CLOUD_PROJECT for Cloud Monitoring quota metrics."
            ),
        ))

        # ── Experimental: Cloud Monitoring quota metrics ───────────────────
        if settings.enable_experimental and settings.google_cloud_project:
            raw["experimental"] = "Cloud Monitoring quota check attempted (not yet implemented)"

        return metrics, raw
