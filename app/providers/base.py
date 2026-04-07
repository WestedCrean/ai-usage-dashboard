"""
Base provider adapter interface.
All provider adapters inherit from BaseProvider and implement fetch().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

from app.models import DataSource, MetricPoint, ProviderKind, ProviderStatus


class BaseProvider(ABC):
    """Abstract base for all provider adapters."""

    id: str = ""                    # slug, e.g. "openai"
    display_name: str = ""          # human label, e.g. "OpenAI"
    kind: ProviderKind = ProviderKind.API
    base_url: str = ""

    def __init__(self) -> None:
        self._configured: bool = self._check_configured()

    @abstractmethod
    def _check_configured(self) -> bool:
        """Return True if required credentials are present."""
        ...

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> tuple[list[MetricPoint], Any]:
        """
        Fetch usage data from the provider.

        Returns:
            metrics: normalized list of MetricPoints
            raw:     raw API response (dict/list) for snapshot storage; None if unavailable
        """
        ...

    @property
    def configured(self) -> bool:
        return self._configured

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            id=self.id,
            display_name=self.display_name,
            kind=self.kind,
            configured=self._configured,
            data_source=DataSource.UNAVAILABLE if not self._configured else DataSource.OFFICIAL,
        )

    async def health_check(self, client: httpx.AsyncClient) -> ProviderStatus:
        """Quick connectivity check — override per provider if needed."""
        if not self._configured:
            return self.status()
        import time
        start = time.monotonic()
        try:
            resp = await client.get(self.base_url, timeout=5.0)
            latency = (time.monotonic() - start) * 1000
            return ProviderStatus(
                id=self.id,
                display_name=self.display_name,
                kind=self.kind,
                configured=True,
                reachable=resp.status_code < 500,
                last_checked=datetime.utcnow(),
                data_source=DataSource.OFFICIAL,
            )
        except Exception as exc:
            return ProviderStatus(
                id=self.id,
                display_name=self.display_name,
                kind=self.kind,
                configured=True,
                reachable=False,
                last_checked=datetime.utcnow(),
                error=str(exc),
                data_source=DataSource.OFFICIAL,
            )
