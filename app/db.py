"""
SQLite persistence layer using aiosqlite.
Stores refresh runs, raw snapshots, normalized metric points, and endpoint test results.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from app.config import get_settings
from app.models import (
    DataSource,
    EndpointTestResult,
    MetricKind,
    MetricPoint,
    RefreshRun,
    TestStatus,
    TimeseriesPoint,
)

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        settings = get_settings()
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(str(db_path))
        _db.row_factory = aiosqlite.Row
        await _init_schema(_db)
    return _db


async def _init_schema(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS refresh_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            triggered_by TEXT NOT NULL DEFAULT 'scheduler',
            providers_attempted TEXT NOT NULL DEFAULT '[]',
            providers_succeeded TEXT NOT NULL DEFAULT '[]',
            error       TEXT
        );

        CREATE TABLE IF NOT EXISTS raw_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER REFERENCES refresh_runs(id),
            provider    TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            payload     TEXT NOT NULL   -- JSON blob
        );

        CREATE TABLE IF NOT EXISTS metric_points (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id       INTEGER REFERENCES refresh_runs(id),
            provider     TEXT NOT NULL,
            model        TEXT,
            kind         TEXT NOT NULL,
            value        REAL NOT NULL,
            unit         TEXT NOT NULL,
            source       TEXT NOT NULL DEFAULT 'official',
            period_start TEXT,
            period_end   TEXT,
            captured_at  TEXT NOT NULL,
            notes        TEXT
        );

        CREATE TABLE IF NOT EXISTS endpoint_tests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            provider     TEXT NOT NULL,
            endpoint     TEXT NOT NULL,
            method       TEXT NOT NULL DEFAULT 'GET',
            status_code  INTEGER,
            ok           INTEGER NOT NULL DEFAULT 0,
            latency_ms   REAL,
            notes        TEXT,
            is_experimental INTEGER NOT NULL DEFAULT 0,
            test_status  TEXT NOT NULL DEFAULT 'fail',
            tested_at    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_metric_provider_kind
            ON metric_points (provider, kind, captured_at);

        CREATE INDEX IF NOT EXISTS idx_endpoint_tests_provider
            ON endpoint_tests (provider, tested_at);
    """)
    await db.commit()


# ── Refresh runs ──────────────────────────────────────────────────────────────


async def insert_refresh_run(run: RefreshRun) -> int:
    db = await get_db()
    cur = await db.execute(
        """INSERT INTO refresh_runs (started_at, triggered_by, providers_attempted, providers_succeeded, error)
           VALUES (?, ?, ?, ?, ?)""",
        (
            run.started_at.isoformat(),
            run.triggered_by,
            json.dumps(run.providers_attempted),
            json.dumps(run.providers_succeeded),
            run.error,
        ),
    )
    await db.commit()
    return cur.lastrowid  # type: ignore[return-value]


async def finish_refresh_run(run_id: int, run: RefreshRun) -> None:
    db = await get_db()
    await db.execute(
        """UPDATE refresh_runs
           SET finished_at=?, providers_attempted=?, providers_succeeded=?, error=?
           WHERE id=?""",
        (
            run.finished_at.isoformat() if run.finished_at else None,
            json.dumps(run.providers_attempted),
            json.dumps(run.providers_succeeded),
            run.error,
            run_id,
        ),
    )
    await db.commit()


async def get_last_refresh_run() -> RefreshRun | None:
    db = await get_db()
    row = await (
        await db.execute(
            "SELECT * FROM refresh_runs ORDER BY started_at DESC LIMIT 1"
        )
    ).fetchone()
    if not row:
        return None
    return _row_to_refresh_run(row)


def _row_to_refresh_run(row: aiosqlite.Row) -> RefreshRun:
    return RefreshRun(
        id=row["id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        triggered_by=row["triggered_by"],
        providers_attempted=json.loads(row["providers_attempted"]),
        providers_succeeded=json.loads(row["providers_succeeded"]),
        error=row["error"],
    )


# ── Raw snapshots ─────────────────────────────────────────────────────────────


async def insert_snapshot(run_id: int, provider: str, payload: Any) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO raw_snapshots (run_id, provider, captured_at, payload) VALUES (?, ?, ?, ?)",
        (run_id, provider, datetime.utcnow().isoformat(), json.dumps(payload)),
    )
    await db.commit()


# ── Metric points ─────────────────────────────────────────────────────────────


async def insert_metric_points(run_id: int, points: list[MetricPoint]) -> None:
    db = await get_db()
    await db.executemany(
        """INSERT INTO metric_points
           (run_id, provider, model, kind, value, unit, source, period_start, period_end, captured_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                run_id,
                p.provider,
                p.model,
                p.kind.value,
                p.value,
                p.unit,
                p.source.value,
                p.period_start.isoformat() if p.period_start else None,
                p.period_end.isoformat() if p.period_end else None,
                p.captured_at.isoformat(),
                p.notes,
            )
            for p in points
        ],
    )
    await db.commit()


async def get_latest_metrics() -> list[MetricPoint]:
    """Return the most recent metric point per (provider, model, kind)."""
    db = await get_db()
    rows = await (
        await db.execute("""
            SELECT m.* FROM metric_points m
            INNER JOIN (
                SELECT provider, COALESCE(model, '') AS model, kind, MAX(captured_at) AS max_ts
                FROM metric_points
                GROUP BY provider, COALESCE(model, ''), kind
            ) latest
            ON m.provider = latest.provider
            AND COALESCE(m.model, '') = latest.model
            AND m.kind = latest.kind
            AND m.captured_at = latest.max_ts
        """)
    ).fetchall()
    return [_row_to_metric(r) for r in rows]


async def get_timeseries(
    provider: str | None = None,
    kind: str | None = None,
    limit: int = 500,
) -> list[TimeseriesPoint]:
    db = await get_db()
    conditions: list[str] = []
    params: list[Any] = []
    if provider:
        conditions.append("provider = ?")
        params.append(provider)
    if kind:
        conditions.append("kind = ?")
        params.append(kind)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await (
        await db.execute(
            f"SELECT captured_at, provider, kind, SUM(value) as value FROM metric_points "
            f"{where} GROUP BY captured_at, provider, kind ORDER BY captured_at DESC LIMIT ?",
            params + [limit],
        )
    ).fetchall()
    result = []
    for r in rows:
        try:
            result.append(
                TimeseriesPoint(
                    timestamp=datetime.fromisoformat(r["captured_at"]),
                    provider=r["provider"],
                    kind=MetricKind(r["kind"]),
                    value=r["value"],
                )
            )
        except Exception:
            pass
    return result


def _row_to_metric(row: aiosqlite.Row) -> MetricPoint:
    return MetricPoint(
        provider=row["provider"],
        model=row["model"],
        kind=MetricKind(row["kind"]),
        value=row["value"],
        unit=row["unit"],
        source=DataSource(row["source"]),
        period_start=datetime.fromisoformat(row["period_start"]) if row["period_start"] else None,
        period_end=datetime.fromisoformat(row["period_end"]) if row["period_end"] else None,
        captured_at=datetime.fromisoformat(row["captured_at"]),
        notes=row["notes"],
    )


# ── Endpoint tests ────────────────────────────────────────────────────────────


async def insert_endpoint_test(result: EndpointTestResult) -> None:
    db = await get_db()
    await db.execute(
        """INSERT INTO endpoint_tests
           (provider, endpoint, method, status_code, ok, latency_ms, notes, is_experimental, test_status, tested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            result.provider,
            result.endpoint,
            result.method,
            result.status_code,
            int(result.ok),
            result.latency_ms,
            result.notes,
            int(result.is_experimental),
            result.test_status.value,
            result.tested_at.isoformat(),
        ),
    )
    await db.commit()


async def get_latest_endpoint_tests() -> list[EndpointTestResult]:
    """Return the most recent test result per (provider, endpoint)."""
    db = await get_db()
    rows = await (
        await db.execute("""
            SELECT t.* FROM endpoint_tests t
            INNER JOIN (
                SELECT provider, endpoint, MAX(tested_at) AS max_ts
                FROM endpoint_tests
                GROUP BY provider, endpoint
            ) latest
            ON t.provider = latest.provider
            AND t.endpoint = latest.endpoint
            AND t.tested_at = latest.max_ts
            ORDER BY t.provider, t.endpoint
        """)
    ).fetchall()
    results = []
    for r in rows:
        # Handle legacy rows that may lack test_status column
        try:
            ts = TestStatus(r["test_status"])
        except (KeyError, ValueError):
            ts = TestStatus.PASS if bool(r["ok"]) else TestStatus.FAIL
        results.append(EndpointTestResult(
            provider=r["provider"],
            endpoint=r["endpoint"],
            method=r["method"],
            status_code=r["status_code"],
            ok=bool(r["ok"]),
            latency_ms=r["latency_ms"],
            notes=r["notes"],
            is_experimental=bool(r["is_experimental"]),
            test_status=ts,
            tested_at=datetime.fromisoformat(r["tested_at"]),
        ))
    return results
