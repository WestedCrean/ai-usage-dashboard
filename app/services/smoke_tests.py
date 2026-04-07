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
from app.models import EndpointTestResult, TestStatus

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
    # Community-discovered usage endpoint — may break without notice.
    if settings.claude_code_session:
        org_id = settings.claude_code_org_id
        if org_id:
            entries.append((
                "claude_code",
                f"https://claude.ai/api/organizations/{org_id}/usage",
                "GET",
                True,
                "Claude Code usage (experimental — requires session cookie + org ID)",
            ))
        else:
            # Fall back to org discovery endpoint
            entries.append((
                "claude_code",
                "https://claude.ai/api/organizations",
                "GET",
                True,
                "Claude Code org discovery (experimental — requires session cookie)",
            ))

    # ── Mistral Vibe ──────────────────────────────────────────────────────
    # Hidden console endpoint for subscription usage
    if settings.mistral_vibe_session:
        entries.append((
            "mistral_vibe",
            "https://console.mistral.ai/api/billing/v2/vibe-usage",
            "GET",
            True,
            "Mistral Vibe usage (experimental — requires console session cookie)",
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


def _get_skipped_providers(settings) -> list[EndpointTestResult]:
    """Return explicit SKIPPED results for providers without credentials."""
    skipped: list[EndpointTestResult] = []
    now = datetime.utcnow()

    provider_key_map = [
        ("openai", settings.openai_api_key, "https://api.openai.com/v1/models"),
        ("anthropic", settings.anthropic_api_key, "https://api.anthropic.com/v1/models"),
        ("gemini", settings.gemini_api_key, "https://generativelanguage.googleapis.com/v1beta/models"),
        ("mistral", settings.mistral_api_key, "https://api.mistral.ai/v1/models"),
        ("openrouter", settings.openrouter_api_key, "https://openrouter.ai/api/v1/auth/key"),
    ]

    for provider, key, endpoint in provider_key_map:
        if not key:
            skipped.append(EndpointTestResult(
                provider=provider,
                endpoint=endpoint,
                method="GET",
                status_code=None,
                ok=False,
                latency_ms=None,
                notes="API key not configured — skipped",
                is_experimental=False,
                test_status=TestStatus.SKIPPED,
                tested_at=now,
            ))

    return skipped


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
    elif "api.mistral.ai" in url and settings.mistral_api_key:
        headers["Authorization"] = f"Bearer {settings.mistral_api_key}"
    elif "openrouter.ai" in url and settings.openrouter_api_key:
        headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
    elif "claude.ai" in url and settings.claude_code_session:
        headers["Cookie"] = f"sessionKey={settings.claude_code_session}"
        headers["User-Agent"] = "ai-usage-dashboard/0.1"
    elif "console.mistral.ai" in url and settings.mistral_vibe_session:
        headers["Cookie"] = settings.mistral_vibe_session
        headers["User-Agent"] = "ai-usage-dashboard/0.1"

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

        # Attempt to parse JSON for additional honesty
        result_notes = notes
        parseable = False
        if ok:
            try:
                resp.json()
                parseable = True
            except Exception:
                result_notes += " | Response not valid JSON"
        else:
            result_notes += f" | HTTP {resp.status_code}: {resp.text[:100]}"

        test_status = TestStatus.PASS if (ok and parseable) else TestStatus.FAIL

        return EndpointTestResult(
            provider=provider,
            endpoint=url,
            method=method,
            status_code=resp.status_code,
            ok=ok and parseable,
            latency_ms=round(latency, 1),
            notes=result_notes,
            is_experimental=is_experimental,
            test_status=test_status,
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
            test_status=TestStatus.FAIL,
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
            test_status=TestStatus.FAIL,
        )


async def run_smoke_tests() -> list[EndpointTestResult]:
    """Run all configured endpoint tests and persist results."""
    settings = get_settings()

    endpoints = _get_official_endpoints(settings) + _get_experimental_endpoints(settings)
    skipped = _get_skipped_providers(settings)

    results: list[EndpointTestResult] = list(skipped)

    if endpoints:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [
                _test_one(client, settings, *entry)
                for entry in endpoints
            ]
            tested = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(tested)

    # Persist results
    for r in results:
        await db.insert_endpoint_test(r)
        status_label = r.test_status.value.upper()
        logger.info(
            "[%s] %s %s -> %s (%s%s)",
            status_label, r.provider, r.endpoint,
            r.status_code or "n/a",
            f"{r.latency_ms:.0f}ms" if r.latency_ms else "—",
            " [experimental]" if r.is_experimental else "",
        )

    ok_count = sum(1 for r in results if r.test_status == TestStatus.PASS)
    skip_count = sum(1 for r in results if r.test_status == TestStatus.SKIPPED)
    fail_count = sum(1 for r in results if r.test_status == TestStatus.FAIL)
    logger.info(
        "Smoke tests complete: %d passed, %d failed, %d skipped",
        ok_count, fail_count, skip_count,
    )
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
        if r.test_status == TestStatus.PASS:
            status = "[green]PASS[/green]"
        elif r.test_status == TestStatus.SKIPPED:
            status = "[yellow]SKIP[/yellow]"
        else:
            status = "[red]FAIL[/red]"
        latency = f"{r.latency_ms:.0f}ms" if r.latency_ms else "—"
        kind = "[yellow]experimental[/yellow]" if r.is_experimental else "official"
        table.add_row(r.provider, r.endpoint[:60], status, latency, r.notes or "", kind)

    console.print(table)


if __name__ == "__main__":
    asyncio.run(_main())
