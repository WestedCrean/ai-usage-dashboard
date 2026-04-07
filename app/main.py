"""
AI Usage Dashboard — FastAPI application entrypoint.

Run with:
    uv run uvicorn app.main:app --reload
or:
    uv run python -m app.main
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app import db
from app.models import (
    DataSource,
    EndpointTestResult,
    MetricKind,
    ModelBreakdown,
    OverviewResponse,
    ProviderCard,
    RefreshRun,
    RefreshStatus,
    TimeseriesPoint,
    UsageWindow,
)
from app.scheduler import get_next_run, start_scheduler, stop_scheduler
from app.services import collector, metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Usage Dashboard")
    await db.get_db()          # Initialize schema
    start_scheduler()

    # Run an initial refresh at startup (don't wait for first scheduled run)
    try:
        await collector.run_refresh(triggered_by="startup")
        logger.info("Initial refresh complete")
    except Exception as exc:
        logger.warning("Initial refresh failed: %s", exc)

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Usage Dashboard",
    description="Tracks AI API usage across OpenAI, Anthropic, Gemini, Mistral, and OpenRouter",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Static files + Jinja2 templates ───────────────────────────────────────────
_base = Path(__file__).parent
_static_dir = _base / "static"
_static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(_base / "templates"))
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ── Health ─────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Dashboard UI ───────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")


# ── API: Overview ──────────────────────────────────────────────────────────────


@app.get("/api/overview", response_model=OverviewResponse, tags=["metrics"])
async def get_overview():
    """Top-level KPI summary: total cost, tokens, requests, provider counts."""
    return await metrics.get_overview(next_refresh=get_next_run())


# ── API: Providers ────────────────────────────────────────────────────────────


@app.get("/api/providers", response_model=list[ProviderCard], tags=["metrics"])
async def get_providers():
    """Per-provider status and latest metrics."""
    return await metrics.get_provider_cards()


# ── API: Models ───────────────────────────────────────────────────────────────


@app.get("/api/models", response_model=list[ModelBreakdown], tags=["metrics"])
async def get_models():
    """Per-model breakdown: tokens, cost, requests."""
    return await metrics.get_model_breakdown()


# ── API: Windows ──────────────────────────────────────────────────────────────


@app.get("/api/windows", response_model=list[UsageWindow], tags=["metrics"])
async def get_windows():
    """Usage window summaries with reset times."""
    return await metrics.get_windows()


# ── API: Timeseries ───────────────────────────────────────────────────────────


@app.get("/api/timeseries", response_model=list[TimeseriesPoint], tags=["metrics"])
async def get_timeseries(
    provider: str | None = Query(default=None, description="Filter by provider slug"),
    kind: str | None = Query(default=None, description="Filter by metric kind"),
    limit: int = Query(default=500, le=2000),
):
    """Historical metric data for charting."""
    return await db.get_timeseries(provider=provider, kind=kind, limit=limit)


# ── API: Tests ────────────────────────────────────────────────────────────────


@app.get("/api/tests", response_model=list[EndpointTestResult], tags=["testing"])
async def get_tests():
    """Latest endpoint smoke test results."""
    return await db.get_latest_endpoint_tests()


@app.post("/api/tests/run", response_model=list[EndpointTestResult], tags=["testing"])
async def run_tests():
    """Run endpoint smoke tests against all configured providers."""
    from app.services.smoke_tests import run_smoke_tests
    return await run_smoke_tests()


# ── API: Refresh ──────────────────────────────────────────────────────────────


@app.post("/api/refresh", response_model=RefreshRun, tags=["system"])
async def manual_refresh():
    """Trigger an immediate refresh across all providers."""
    run = await collector.run_refresh(triggered_by="manual")
    return run


# ── Refresh status (used by UI polling) ───────────────────────────────────────


@app.get("/api/refresh/status", response_model=RefreshStatus, tags=["system"])
async def refresh_status():
    settings = get_settings()
    last_run = await db.get_last_refresh_run()
    return RefreshStatus(
        last_run=last_run,
        next_run_at=get_next_run(),
        interval_minutes=settings.refresh_interval_minutes,
    )


# ── Main entry ────────────────────────────────────────────────────────────────


def main() -> None:
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
