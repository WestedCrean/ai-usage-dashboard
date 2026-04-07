"""
Background scheduler — runs a refresh every N minutes (default: 15).
Uses APScheduler with AsyncIO executor.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_next_run: datetime | None = None


def get_next_run() -> datetime | None:
    return _next_run


async def _scheduled_refresh() -> None:
    global _next_run
    from app.services.collector import run_refresh
    logger.info("Scheduler: starting automatic refresh")
    try:
        run = await run_refresh(triggered_by="scheduler")
        logger.info(
            "Scheduler: refresh complete — %d/%d providers succeeded",
            len(run.providers_succeeded),
            len(run.providers_attempted),
        )
    except Exception as exc:
        logger.error("Scheduler: refresh failed: %s", exc)
    finally:
        settings = get_settings()
        _next_run = datetime.utcnow() + timedelta(minutes=settings.refresh_interval_minutes)


def start_scheduler() -> None:
    global _scheduler, _next_run
    settings = get_settings()
    interval = settings.refresh_interval_minutes

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _scheduled_refresh,
        trigger=IntervalTrigger(minutes=interval),
        id="auto_refresh",
        name="AI Usage Auto-Refresh",
        replace_existing=True,
    )
    _scheduler.start()
    _next_run = datetime.utcnow() + timedelta(minutes=interval)
    logger.info("Scheduler started — refresh every %d minutes", interval)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
