"""
Data collector — orchestrates all provider adapters in parallel,
stores snapshots and normalized metrics, and records the refresh run.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from app import db
from app.models import RefreshRun
from app.providers.anthropic import AnthropicProvider
from app.providers.gemini import GeminiProvider
from app.providers.mistral import MistralProvider
from app.providers.openai import OpenAIProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.tool_usage import (
    ClaudeCodeProvider,
    CodexProvider,
    GeminiCLIProvider,
    MistralVibeProvider,
)
from app.providers.base import BaseProvider


# Registry of all provider adapters (instantiated once at startup)
ALL_PROVIDERS: list[BaseProvider] = [
    OpenAIProvider(),
    AnthropicProvider(),
    GeminiProvider(),
    MistralProvider(),
    OpenRouterProvider(),
    CodexProvider(),
    ClaudeCodeProvider(),
    GeminiCLIProvider(),
    MistralVibeProvider(),
]


async def _fetch_one(
    provider: BaseProvider,
    client: httpx.AsyncClient,
    run_id: int,
) -> tuple[str, bool]:
    """Fetch from a single provider; persist results. Returns (provider_id, success)."""
    try:
        metrics, raw = await provider.fetch(client)
        if raw is not None:
            await db.insert_snapshot(run_id, provider.id, raw)
        if metrics:
            await db.insert_metric_points(run_id, metrics)
        return provider.id, True
    except Exception as exc:
        await db.insert_snapshot(run_id, provider.id, {"error": str(exc)})
        return provider.id, False


async def run_refresh(triggered_by: str = "scheduler") -> RefreshRun:
    """
    Run a full refresh across all configured providers.
    Returns the completed RefreshRun record.
    """
    now = datetime.utcnow()
    run = RefreshRun(
        started_at=now,
        triggered_by=triggered_by,
        providers_attempted=[p.id for p in ALL_PROVIDERS],
    )
    run_id = await db.insert_refresh_run(run)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=True,
    ) as client:
        tasks = [_fetch_one(p, client, run_id) for p in ALL_PROVIDERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    succeeded = []
    for r in results:
        if isinstance(r, tuple) and r[1]:
            succeeded.append(r[0])

    run.finished_at = datetime.utcnow()
    run.providers_succeeded = succeeded
    run.id = run_id
    await db.finish_refresh_run(run_id, run)

    return run


def get_all_providers() -> list[BaseProvider]:
    return ALL_PROVIDERS
