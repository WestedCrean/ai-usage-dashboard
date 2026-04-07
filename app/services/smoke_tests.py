"""
Endpoint smoke tests — tests official (and optionally experimental) endpoints
for all configured providers. Results are persisted to the database.

Invoked by:
  - POST /api/tests/run
  - CLI: uv run python -m app.services.smoke_tests
"""

from __future__ import annotations

import asyncio
import time
import logging
from datetime import datetime

import httpx

from app import db
from app.config import get_settings
from app.models import EndpointTestResult

logger = logging.getLogger(__name__)


# ── Endpoint registry ─────────────────────────────────────────────────────────
# Each entry: (provider, endpoint_url, method, is_experimental, notes)
# Keys are only included; missing keys skip the entry gracefully.

def _get_official_endpoints(settings) -> list[tuple]:
    """Return list of (provider, url, method, is_experimental, notes) tuples."""
    entries = []

    # ── OpenAI ────────────────────────────────────────────────────────────
    if settings.openai_api_key:
        entries += [
            ("openai", "https://api.openai.com/v1/models", "GET", False, "Model list — public endpoint"),
            ("openai", "https://api.openai.com/v1/usage", "GET", False, "Usage data (org-level)"),
            ("openai", "https://api.openai.com/dashboard/billing/usage", "GET", False, "Billing usage (dashboard endpoint)"),
        ]

    # ── Anthropic ─────────────────────────────────────────────────────────
    if settings.anthropic_api_key:
        entries += [
            ("anthropic", "https://api.anthropic.com/v1/models", "GET", False, "Model list"),
            ("anthropic", "https://api.anthropic.com/v1/usage", "GET", False, "Usage data (beta)"),
        ]

    # ── Gemini ────────────────────────────────────────────────────────────
    if settings.gemini_api_key:
        entries += [
            ("gemini", f"https://generativelanguage.googleapis.com/v1beta/models?key={settings.gemini_api_key}", "GET", False, "Model list"),
        ]

    # ── Mistral ───────────────────────────────────────────────────────────
    if settings.mistral_api_key:
        entries += [
            ("mistral", "https://api.mistral.ai/v1/models", "GET", False, "Model list"),
            ("mistral", "https://api.mistral.ai/v1/organization/billing/summary", "GET", False, "Billing summary"),
        ]

    # ── OpenRouter ────────────────────────────────────────────────────────
    if settings.openrouter_api_key:
        entries += [
            ("openrouter", "https://openrouter.ai/api/v1/auth/key", "GET", False, "Key info & credit balance"),
            ("openrouter", "https://openrouter.ai/api/v1/models", "GET", False, "Model list (public)"),
        ]

    return entries


def _get_experimental_endpoints(settings) -> list[tuple]:
    """Experimental/community-discovered endpoints. Only tested when ENABLE_EXPERIMENTAL=true."""
    if not settings.enable_experimental:
        return []

    entries = []

    # ── Claude Code ───────────────────────────────────────────────────────
    # Community-discovered analytics endpoint — may break without notice.
    if settings.claude_code_session:
        entries.append((
            "claude_code",
            "https://api.claude.ai/api/organizations/usage",
            "GET",
            True,
            "Claude Code usage analytics (community endpoint — requires session cookie)",
        ))

    # ── OpenAI org usage ──────────────────────────────────────────────────
    # Organization-level usage endpoint (documented but access-gated)
    if settings.openai_api_key and settings.openai_org_id:
        entries.append((
            "openai",
            "https://api.openai.com/v1/organization/usage/completions",
            "GET",
            True,
            "Org-level completions usage (access-gated, requires org ID)",
        ))

    return entries


async def _test_one(
    client: httpx.AsyncClient,
    settings,
    provider: str,
    url: str,
    method: str,
    is_experimental: bool,
    notes: str,
) -> EndpointTestResult:
    headers = {}
    # Attach appropriate auth headers
    if "openai.com" in url and settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
        if settings.openai_org_id:
            headers["OpenAI-Organization"] = settings.openai_org_id
    elif "anthropic.com" in url and settings.anthropic_api_key:
        headers["x-api-key"] = settings.anthropic_api_key
        headers["anthropic-version"] = "2023-06-01"
        headers["anthropic-beta"] = "usage-2025-01-01"
    elif "mistral.ai" in url and settings.mistral_api_key:
        headers["Authorization"] = f"Bearer {settings.mistral_api_key}"
    elif "openrouter.ai" in url and settings.openrouter_api_key:
        headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
    elif "claude.ai" in url and settings.claude_code_session:
        headers["Cookie"] = f"sessionKey={settings.claude_code_session}"

    t0 = time.monotonic()
    try:
        resp = await client.request(
            method,
            url,
            headers=headers,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        latency = (time.monotonic() - t0) * 1000
        ok = resp.status_code < 400
        result_notes = notes
        if not ok:
            result_notes += f" | Response: {resp.text[:100]}"
        return EndpointTestResult(
            provider=provider,
            endpoint=url,
            method=method,
            status_code=resp.status_code,
            ok=ok,
            latency_ms=round(latency, 1),
            notes=result_notes,
            is_experimental=is_experimental,
        )
    except httpx.TimeoutException:
        latency = (time.monotonic() - t0) * 1000
        return EndpointTestResult(
            provider=provider,
            endpoint=url,
            method=method,
            status_code=None,
            ok=False,
            latency_ms=round(latency, 1),
            notes=notes + " | Timeout",
            is_experimental=is_experimental,
        )
    except Exception as exc:
        latency = (time.monotonic() - t0) * 1000
        return EndpointTestResult(
            provider=provider,
            endpoint=url,
            method=method,
            status_code=None,
            ok=False,
            latency_ms=round(latency, 1),
            notes=notes + f" | Error: {exc}",
            is_experimental=is_experimental,
        )


async def run_smoke_tests() -> list[EndpointTestResult]:
    """Run all configured endpoint tests and persist results."""
    settings = get_settings()

    endpoints = _get_official_endpoints(settings) + _get_experimental_endpoints(settings)

    if not endpoints:
        logger.info("No endpoints to test (no API keys configured)")
        return []

    results: list[EndpointTestResult] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [
            _test_one(client, settings, *entry)
            for entry in endpoints
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    # Persist results
    for r in results:
        await db.insert_endpoint_test(r)
        status_str = "OK" if r.ok else "FAIL"
        logger.info(
            "[%s] %s %s → %s (%s%s)",
            status_str, r.provider, r.endpoint,
            r.status_code or "n/a",
            f"{r.latency_ms:.0f}ms" if r.latency_ms else "—",
            " [experimental]" if r.is_experimental else "",
        )

    ok_count = sum(1 for r in results if r.ok)
    logger.info("Smoke tests complete: %d/%d passed", ok_count, len(results))
    return results


# ── CLI runner ────────────────────────────────────────────────────────────────

async def _main():
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("[bold cyan]AI Usage Dashboard — Endpoint Smoke Tests[/bold cyan]\n")

    await db.get_db()
    results = await run_smoke_tests()

    if not results:
        console.print("[yellow]No tests run. Configure at least one API key.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold dim")
    table.add_column("Provider", style="cyan")
    table.add_column("Endpoint")
    table.add_column("Status", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("Notes")
    table.add_column("Type", justify="center")

    for r in results:
        status = "[green]OK[/green]" if r.ok else "[red]FAIL[/red]"
        latency = f"{r.latency_ms:.0f}ms" if r.latency_ms else "—"
        kind = "[yellow]experimental[/yellow]" if r.is_experimental else "official"
        table.add_row(r.provider, r.endpoint[:60], status, latency, r.notes or "", kind)

    console.print(table)


if __name__ == "__main__":
    asyncio.run(_main())
