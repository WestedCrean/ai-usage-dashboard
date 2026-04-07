"""
Tool/CLI usage adapter — covers subscription and coding assistant tools:
  - OpenAI Codex (subscription window)
  - Claude Code (subscription window)
  - Gemini CLI (subscription / free tier window)
  - Mistral Vibe (subscription window)

These tools do NOT expose public machine-readable usage APIs.
Data source is UNAVAILABLE unless experimental endpoints are explicitly enabled.

Each tool is modeled as a ProviderKind.TOOL entry that shows in the UI
with the appropriate empty/limited state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.models import DataSource, MetricKind, MetricPoint, ProviderKind, ProviderStatus
from app.providers.base import BaseProvider


class _ToolBaseProvider(BaseProvider):
    """Shared base for subscription/CLI tools."""
    kind = ProviderKind.TOOL

    # Override in subclass
    _tool_note: str = ""
    _experimental_note: str = ""

    def _check_configured(self) -> bool:
        # Subclasses override to indicate when the tool should be visible.
        return False

    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        # Emit a single UNAVAILABLE metric so the UI can show the tool card
        metrics = [
            MetricPoint(
                provider=self.id,
                kind=MetricKind.COST_USD,
                value=0.0,
                unit="USD",
                source=DataSource.UNAVAILABLE,
                notes=self._tool_note,
            )
        ]
        raw: dict[str, Any] = {"note": self._tool_note}

        # Optional experimental fetch
        await self._fetch_experimental(client, metrics, raw)

        return metrics, raw

    async def _fetch_experimental(
        self,
        client: httpx.AsyncClient,
        metrics: list[MetricPoint],
        raw: dict[str, Any],
    ) -> None:
        """Override in subclasses that have experimental endpoints."""
        pass


class CodexProvider(_ToolBaseProvider):
    id = "codex"
    display_name = "OpenAI Codex"
    _tool_note = (
        "OpenAI Codex CLI usage is not exposed via a public API. "
        "Usage is billed through your OpenAI account and visible under OpenAI billing."
    )

    def _check_configured(self) -> bool:
        # Show Codex card when OpenAI key is present (usage appears under OpenAI billing)
        return bool(get_settings().openai_api_key)


class ClaudeCodeProvider(_ToolBaseProvider):
    id = "claude_code"
    display_name = "Claude Code"
    _tool_note = (
        "Claude Code subscription usage is not exposed via a public API. "
        "Session-level analytics exist as an experimental endpoint (gated behind ENABLE_EXPERIMENTAL)."
    )

    def _check_configured(self) -> bool:
        settings = get_settings()
        # Show when Anthropic key is present OR experimental session is configured
        return bool(settings.anthropic_api_key) or (
            settings.enable_experimental and bool(settings.claude_code_session)
        )

    async def _resolve_org_id(
        self,
        client: httpx.AsyncClient,
        settings,
    ) -> str | None:
        """Best-effort org ID resolution via /api/organizations discovery."""
        if settings.claude_code_org_id:
            return settings.claude_code_org_id

        try:
            resp = await client.get(
                "https://claude.ai/api/organizations",
                headers={
                    "Cookie": f"sessionKey={settings.claude_code_session}",
                    "User-Agent": "ai-usage-dashboard/0.1",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            orgs = resp.json()
            # Response is typically a list of org objects; take the first one
            if isinstance(orgs, list) and orgs:
                return orgs[0].get("uuid") or orgs[0].get("id")
        except Exception:
            pass
        return None

    async def _fetch_experimental(
        self,
        client: httpx.AsyncClient,
        metrics: list[MetricPoint],
        raw: dict[str, Any],
    ) -> None:
        settings = get_settings()
        if not settings.enable_experimental or not settings.claude_code_session:
            return

        # Step 1: Resolve org ID (explicit config or auto-discover)
        org_id = await self._resolve_org_id(client, settings)
        raw["resolved_org_id"] = org_id

        if not org_id:
            raw["experimental_error"] = (
                "Could not resolve Claude Code organization ID. "
                "Set CLAUDE_CODE_ORG_ID in .env or ensure session cookie is valid."
            )
            return

        # Step 2: Fetch usage — community-discovered endpoint, may break at any time.
        # GET https://claude.ai/api/organizations/{org_id}/usage
        try:
            resp = await client.get(
                f"https://claude.ai/api/organizations/{org_id}/usage",
                headers={
                    "Cookie": f"sessionKey={settings.claude_code_session}",
                    "User-Agent": "ai-usage-dashboard/0.1",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["experimental_usage"] = data

            # Parse known response shape: five_hour.utilization, seven_day.utilization,
            # extra_usage.monthly_limit, used_credits
            five_hour = data.get("five_hour", {})
            seven_day = data.get("seven_day", {})
            extra = data.get("extra_usage", {})

            utilization = five_hour.get("utilization") or seven_day.get("utilization")
            if utilization is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.RATE_LIMIT_USED,
                    value=float(utilization) * 100,
                    unit="percent",
                    source=DataSource.EXPERIMENTAL,
                    notes="Claude Code 5-hour utilization (experimental)",
                ))

            monthly_limit = extra.get("monthly_limit")
            used_credits = extra.get("used_credits") or data.get("used_credits")
            if monthly_limit is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.RATE_LIMIT_TOTAL,
                    value=float(monthly_limit),
                    unit="USD",
                    source=DataSource.EXPERIMENTAL,
                    notes="Claude Code extra usage monthly limit (experimental)",
                ))
            if used_credits is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.CREDITS_USED,
                    value=float(used_credits),
                    unit="USD",
                    source=DataSource.EXPERIMENTAL,
                    notes="Claude Code used credits (experimental)",
                ))

            # Fallback: legacy token-based parsing
            tokens = data.get("total_tokens") or data.get("tokens")
            if tokens:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.TOKENS_INPUT,
                    value=float(tokens),
                    unit="tokens",
                    source=DataSource.EXPERIMENTAL,
                    notes="Claude Code analytics (experimental community endpoint)",
                ))
        except Exception as exc:
            raw["experimental_error"] = str(exc)


class GeminiCLIProvider(_ToolBaseProvider):
    id = "gemini_cli"
    display_name = "Gemini CLI"
    _tool_note = (
        "Gemini CLI usage is tied to your Google account free tier or Gemini Advanced subscription. "
        "No public machine-readable usage API is available."
    )

    def _check_configured(self) -> bool:
        return bool(get_settings().gemini_api_key)


class MistralVibeProvider(_ToolBaseProvider):
    id = "mistral_vibe"
    display_name = "Mistral Vibe"
    _tool_note = (
        "Mistral Vibe is a subscription coding assistant. "
        "Usage data is not available via a public API."
    )

    def _check_configured(self) -> bool:
        settings = get_settings()
        # Show when Mistral API key is present OR experimental Vibe session is configured
        return bool(settings.mistral_api_key) or (
            settings.enable_experimental and bool(settings.mistral_vibe_session)
        )

    async def _fetch_experimental(
        self,
        client: httpx.AsyncClient,
        metrics: list[MetricPoint],
        raw: dict[str, Any],
    ) -> None:
        settings = get_settings()
        if not settings.enable_experimental or not settings.mistral_vibe_session:
            return

        # Hidden console endpoint: GET https://console.mistral.ai/api/billing/v2/vibe-usage
        # Response includes vibe.models.*, usage_percentage, reset_at, start_date, end_date.
        try:
            resp = await client.get(
                "https://console.mistral.ai/api/billing/v2/vibe-usage",
                headers={
                    "Cookie": settings.mistral_vibe_session,
                    "User-Agent": "ai-usage-dashboard/0.1",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["experimental_vibe_usage"] = data

            # Parse known response shape
            usage_pct = data.get("usage_percentage")
            if usage_pct is not None:
                metrics.append(MetricPoint(
                    provider=self.id,
                    kind=MetricKind.RATE_LIMIT_USED,
                    value=float(usage_pct),
                    unit="percent",
                    source=DataSource.EXPERIMENTAL,
                    notes="Mistral Vibe usage percentage (experimental console endpoint)",
                ))

            reset_at = data.get("reset_at")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            # Extract per-model usage if present (vibe.models.*)
            models = data.get("models") or data.get("vibe", {}).get("models", {})
            if isinstance(models, dict):
                for model_name, model_data in models.items():
                    tokens_in = model_data.get("input_tokens", 0)
                    tokens_out = model_data.get("output_tokens", 0)
                    if tokens_in:
                        metrics.append(MetricPoint(
                            provider=self.id,
                            model=model_name,
                            kind=MetricKind.TOKENS_INPUT,
                            value=float(tokens_in),
                            unit="tokens",
                            source=DataSource.EXPERIMENTAL,
                            notes="Mistral Vibe model usage (experimental)",
                        ))
                    if tokens_out:
                        metrics.append(MetricPoint(
                            provider=self.id,
                            model=model_name,
                            kind=MetricKind.TOKENS_OUTPUT,
                            value=float(tokens_out),
                            unit="tokens",
                            source=DataSource.EXPERIMENTAL,
                            notes="Mistral Vibe model usage (experimental)",
                        ))

        except Exception as exc:
            raw["experimental_vibe_error"] = str(exc)
