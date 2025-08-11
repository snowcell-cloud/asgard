"""Pydantic models for Airbyte API payloads."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Workspace(BaseModel):
    workspace_id: UUID = Field(alias="workspaceId")
    name: str

    class Config:
        populate_by_name = True


class ConnectionCreateRequest(BaseModel):
    source_id: UUID = Field(alias="sourceId")
    destination_id: UUID = Field(alias="destinationId")
    name: str
    sync_catalog: dict[str, Any] = Field(alias="syncCatalog")
    schedule: Optional[dict[str, Any]] = None
    status: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "allow"


class ConnectionCreateResponse(BaseModel):
    connection_id: UUID = Field(alias="connectionId")

    class Config:
        populate_by_name = True


class SyncResponse(BaseModel):
    job_id: int = Field(alias="jobId")

    class Config:
        populate_by_name = True


class JobStatusResponse(BaseModel):
    job: dict[str, Any]
