"""Airbyte API client."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator

import httpx

from app.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AirbyteClientError(Exception):
    """Raised when the Airbyte API returns an error response."""

    status_code: int
    message: str

class AirbyteClient:
    """Client for interacting with the Airbyte HTTP API."""

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or settings.airbyte_base_url
        
        logger.info(f"=== AirbyteClient Initialization ===")
        logger.info(f"Environment: {getattr(settings, 'environment', 'not set')}")
        logger.info(f"Requested base_url: {base_url}")
        logger.info(f"Settings airbyte_base_url: {settings.airbyte_base_url}")
        logger.info(f"Final base_url: {self.base_url}")
        logger.info("=====================================")
        
        # Create the httpx client immediately for non-async context manager usage
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0  # Add timeout for better error handling
        )
        logger.debug("HTTP client initialized")

    async def __aenter__(self) -> "AirbyteClient":
        logger.debug("Entering AirbyteClient async context")
        # Client is already initialized in __init__
        return self

    async def __aexit__(self, *exc_info) -> None:  # pragma: no cover - infrastructure
        logger.debug("Exiting AirbyteClient async context")
        if self._client:
            await self._client.aclose()

    async def close(self) -> None:  # pragma: no cover - compatibility
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.debug("HTTP client closed")

    async def _post(self, path: str, payload: dict | None = None) -> dict:
        logger.info(f"Making POST request to {path}")
        try:
            resp = await self._client.post(path, json=payload or {})
            logger.debug(f"Response status: {resp.status_code}")
            resp.raise_for_status()
            result = resp.json()
            if result is None:
                logger.warning(f"Received None response from {path}")
                result = {}
            logger.debug(f"Response data: {result}")
            return result
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure
            detail = exc.response.text
            logger.error(f"HTTP error {exc.response.status_code}: {detail}")
            raise AirbyteClientError(exc.response.status_code, detail) from exc

    async def  _get(self, path: str) -> dict:
        logger.info(f"Making GET request to {path}")
        try:
            if self._client is None:
                raise RuntimeError("HTTP client is not initialized")
            
            resp = await self._client.get(path)
            logger.debug(f"Response status: {resp.status_code}")
            logger.debug(f"Response headers: {dict(resp.headers)}")
            resp.raise_for_status()
            
            # Get raw response text first
            raw_text = resp.text
            logger.debug(f"Raw response text: {raw_text}")
            
            result = resp.json()
            logger.debug(f"Parsed JSON result: {result}")
            logger.debug(f"Result type: {type(result)}")
            
            if result is None:
                logger.warning(f"Received None response from {path}")
                result = {}
            return result
        except Exception as exc:
            logger.error(f"Exception in _get({path}): {type(exc).__name__}: {exc}")
            if isinstance(exc, httpx.HTTPStatusError):
                detail = exc.response.text
                logger.error(f"HTTP error {exc.response.status_code}: {detail}")
                raise AirbyteClientError(exc.response.status_code, detail) from exc
            raise
    

    async def list_workspaces(self) -> list[dict]:
        """Return all workspaces configured in Airbyte."""
        logger.info("Fetching workspaces list")
        try:
            data = await self._get("/workspaces")
            if data is None:
                logger.error("Received None response from /workspaces endpoint")
                return []
            
            # Handle both "data" and "workspaces" keys for different API versions
            workspaces = data.get("data", data.get("workspaces", []))
            logger.info(f"Found {len(workspaces)} workspaces")
            logger.debug(f"Raw API response: {data}")
            logger.debug(f"Extracted workspaces: {workspaces}")
            return workspaces
        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")
            raise

    async def list_source_definitions(self, workspace_id: str) -> list[dict]:
        """Return available source connector definitions."""
        logger.info("Fetching source definitions")
        try:
            data = await self._get(f"/workspaces/{workspace_id}/definitions/sources")
            if data is None:
                logger.error("Received None response from /workspaces/workspaceId/definitions/sources endpoint")
                return []
            
            # Handle both "data" and "sourceDefinitions" keys for different API versions
            definitions = data.get("data", data.get("sourceDefinitions", []))
            logger.info(f"Found {len(definitions)} source definitions")
            logger.debug(f"Raw API response: {data}")
            return definitions
        except Exception as e:
            logger.error(f"Error listing source definitions: {e}")
            raise

    async def list_destination_definitions(self) -> list[dict]:
        """Return available destination connector definitions."""
        data = await self._post("/destination_definitions/list")
        return data.get("destinationDefinitions", [])

    async def create_source(self, payload: dict) -> dict:
        """Create a new source in Airbyte."""
        logger.info(f"Creating source with configuration")
        try:
            result = await self._post("/sources", payload)
            logger.info(f"Source created successfully: {result.get('sourceId', 'Unknown ID')}")
            return result
        except Exception as e:
            logger.error(f"Error creating source: {e}")
            raise

    async def create_destination(self, payload: dict) -> dict:
        """Create a new destination in Airbyte."""
        return await self._post("/destinations", payload)

    async def list_sources(self, workspace_id: str) -> list[dict]:
        """List all sources in a workspace."""
        logger.info(f"Listing sources for workspace: {workspace_id}")
        try:
            result = await self._get("/sources")
            sources = result.get("data", [])
            logger.info(f"Found {len(sources)} sources")
            return sources
        except Exception as e:
            logger.error(f"Error listing sources: {e}")
            raise

    async def list_destinations(self, workspace_id: str) -> list[dict]:
        """List all destinations in a workspace."""
        logger.info(f"Listing destinations for workspace: {workspace_id}")
        try:
            result = await self._get("/destinations")
            destinations = result.get("data", [])
            logger.info(f"Found {len(destinations)} destinations")
            return destinations
        except Exception as e:
            logger.error(f"Error listing destinations: {e}")
            raise

    async def create_connection(self, payload: dict) -> dict:
        """Create a connection between an existing source and destination."""
        return await self._post("/connections", payload)

@asynccontextmanager
async def get_airbyte_client() -> AsyncGenerator[AirbyteClient, None]:
    settings = get_settings()
    async with AirbyteClient(settings.airbyte_base_url) as client:
        yield client

def get_airbyte_client_dependency() -> AirbyteClient:
    """FastAPI dependency to get an Airbyte client instance."""
    logger.info("Creating AirbyteClient dependency")
    try:
        settings = get_settings()
        client = AirbyteClient(settings.airbyte_base_url)
        logger.debug(f"AirbyteClient created: {type(client)}")
        return client
    except Exception as e:
        logger.error(f"Error creating AirbyteClient: {e}")
        raise
