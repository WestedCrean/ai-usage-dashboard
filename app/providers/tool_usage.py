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
        # Tools don't require an API key for basic display
        return True

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


class ClaudeCodeProvider(_ToolBaseProvider):
    id = "claude_code"
    display_name = "Claude Code"
    _tool_note = (
        "Claude Code subscription usage is not exposed via a public API. "
        "Session-level analytics exist as an experimental endpoint (gated behind ENABLE_EXPERIMENTAL)."
    )

    async def _fetch_experimental(
        self,
        client: httpx.AsyncClient,
        metrics: list[MetricPoint],
        raw: dict[str, Any],
    ) -> None:
        settings = get_settings()
        if not settings.enable_experimental or not settings.claude_code_session:
            return

        # Community-discovered analytics endpoint — NOT official, may break at any time.
        # Requires a valid Claude Code session cookie.
        try:
            resp = await client.get(
                "https://api.claude.ai/api/organizations/usage",
                headers={
                    "Cookie": f"sessionKey={settings.claude_code_session}",
                    "User-Agent": "ai-usage-dashboard/0.1",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            raw["experimental_usage"] = data
            # Attempt to extract token data if present
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


class MistralVibeProvider(_ToolBaseProvider):
    id = "mistral_vibe"
    display_name = "Mistral Vibe"
    _tool_note = (
        "Mistral Vibe is a subscription coding assistant. "
        "Usage data is not available via a public API."
    )
