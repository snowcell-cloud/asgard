"""Pydantic models for Airbyte API payloads."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Workspace(BaseModel):
    """Representation of an Airbyte workspace."""

    workspace_id: UUID = Field(alias="workspaceId")
    name: str

    class Config:
        populate_by_name = True


class ConnectionCreateRequest(BaseModel):
    """Payload sent to Airbyte when creating a connection."""

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
    """Response returned after creating a connection."""

    connection_id: UUID = Field(alias="connectionId")

    class Config:
        populate_by_name = True


class SyncResponse(BaseModel):
    """Response payload when a sync is triggered."""

    job_id: int = Field(alias="jobId")

    class Config:
        populate_by_name = True


class JobStatusResponse(BaseModel):
    """Status information for a sync job."""

    job: dict[str, Any]


class SourceCreateRequest(BaseModel):
    """Payload required to create a source."""

    workspace_id: UUID = Field(alias="workspaceId")
    source_definition_id: UUID = Field(alias="sourceDefinitionId")
    name: str
    connection_configuration: dict[str, Any] = Field(alias="connectionConfiguration")

    class Config:
        populate_by_name = True


class SourceCreateResponse(BaseModel):
    """Response returned after creating a source."""

    source_id: UUID = Field(alias="sourceId")

    class Config:
        populate_by_name = True


class DestinationCreateRequest(BaseModel):
    """Payload required to create a destination."""

    workspace_id: UUID = Field(alias="workspaceId")
    destination_definition_id: UUID = Field(alias="destinationDefinitionId")
    name: str
    connection_configuration: dict[str, Any] = Field(alias="connectionConfiguration")

    class Config:
        populate_by_name = True


class DestinationCreateResponse(BaseModel):
    """Response returned after creating a destination."""

    destination_id: UUID = Field(alias="destinationId")

    class Config:
        populate_by_name = True


class ConnectionConfig(BaseModel):
    """Connection settings used when composing a workflow."""

    name: str
    sync_catalog: dict[str, Any] = Field(alias="syncCatalog")
    schedule: Optional[dict[str, Any]] = None
    status: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "allow"


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a full data transfer workflow."""

    source: SourceCreateRequest
    destination: DestinationCreateRequest
    connection: ConnectionConfig
    trigger_sync: bool = False


class WorkflowCreateResponse(BaseModel):
    """Identifiers for objects created as part of a workflow."""

    source_id: UUID = Field(alias="sourceId")
    destination_id: UUID = Field(alias="destinationId")
    connection_id: UUID = Field(alias="connectionId")
    job_id: Optional[int] = Field(default=None, alias="jobId")

    class Config:
        populate_by_name = True
