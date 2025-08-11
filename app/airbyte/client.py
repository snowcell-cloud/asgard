"""Airbyte API client."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

import httpx

from app.config import get_settings


@dataclass
class AirbyteClientError(Exception):
    """Raised when the Airbyte API returns an error response."""

    status_code: int
    message: str


class AirbyteClient:
    """Client for interacting with the Airbyte HTTP API."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def __aenter__(self) -> "AirbyteClient":
        return self

    async def __aexit__(self, *exc_info) -> None:  # pragma: no cover - infrastructure
        await self._client.aclose()

    async def close(self) -> None:  # pragma: no cover - compatibility
        await self._client.aclose()

    async def _post(self, path: str, payload: dict | None = None) -> dict:
        try:
            resp = await self._client.post(path, json=payload or {})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure
            detail = exc.response.text
            raise AirbyteClientError(exc.response.status_code, detail) from exc
        return resp.json()

    async def list_workspaces(self) -> list[dict]:
        data = await self._post("/workspaces/list")
        return data.get("workspaces", [])

    async def create_connection(self, payload: dict) -> dict:
        return await self._post("/connections/create", payload)

    async def trigger_sync(self, connection_id: str) -> dict:
        return await self._post("/connections/sync", {"connectionId": connection_id})

    async def get_job_status(self, job_id: int) -> dict:
        return await self._post("/jobs/get", {"id": job_id})


@asynccontextmanager
async def get_airbyte_client() -> AsyncGenerator[AirbyteClient, None]:
    settings = get_settings()
    async with AirbyteClient(settings.airbyte_base_url) as client:
        yield client
