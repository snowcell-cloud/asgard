"""FastAPI routes for simplified Airbyte interactions."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.airbyte.client import (
    AirbyteClient,
    AirbyteClientError,
    get_airbyte_client,
)
from app.airbyte.schemas import (
    DataSinkPayload,
    DataSinkResponse,
    DataSourcePayload,
    DataSourceResponse,
    IngestionPayload,
    IngestionResponse,
    DataDestinationType,
    DataSourceType,
)

router = APIRouter()

async def _resolve_workspace_id(client: AirbyteClient) -> str:
    """Determine the workspace ID to use for requests."""
    settings = get_settings()
    if settings.airbyte_workspace_id:
        return settings.airbyte_workspace_id
    workspaces = await client.list_workspaces()
    if not workspaces:
        raise HTTPException(status_code=502, detail="no workspaces available")
    return workspaces[0]["workspaceId"]

async def _get_source_definition_id(
    client: AirbyteClient, source_type: DataSourceType
) -> str:
    defs = await client.list_source_definitions()
    for d in defs:
        if d["name"].lower() == source_type.value:
            return d["sourceDefinitionId"]
    raise HTTPException(status_code=400, detail="unsupported source type")

async def _get_destination_definition_id(
    client: AirbyteClient, dest_type: DataDestinationType
) -> str:
    defs = await client.list_destination_definitions()
    for d in defs:
        if d["name"].lower() == dest_type.value:
            return d["destinationDefinitionId"]
    raise HTTPException(status_code=400, detail="unsupported destination type")

# ---------------------------------------------------------------------------
# Public ingestion endpoints
# ---------------------------------------------------------------------------

@router.post("/datasource", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    payload: DataSourcePayload, client: AirbyteClient = Depends(get_airbyte_client)
) -> DataSourceResponse:
    """Create a source via the Airbyte API."""

    workspace_id = await _resolve_workspace_id(client)
    definition_id = await _get_source_definition_id(client, payload.type)

    req = {
        "workspaceId": workspace_id,
        "sourceDefinitionId": definition_id,
        "name": payload.name,
        "connectionConfiguration": payload.config.model_dump(),
    }

    try:
        result = await client.create_source(req)
        return DataSourceResponse(id=str(result["sourceId"]), **payload.model_dump())
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

@router.post("/sink", response_model=DataSinkResponse, status_code=201)
async def create_sink(
    payload: DataSinkPayload, client: AirbyteClient = Depends(get_airbyte_client)
) -> DataSinkResponse:
    """Create a destination via the Airbyte API."""

    workspace_id = await _resolve_workspace_id(client)
    definition_id = await _get_destination_definition_id(client, payload.type)
    req = {
        "workspaceId": workspace_id,
        "destinationDefinitionId": definition_id,
        "name": payload.name,
        "connectionConfiguration": payload.config.model_dump(),
    }

    try:
        result = await client.create_destination(req)
        return DataSinkResponse(id=str(result["destinationId"]), **payload.model_dump())
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

@router.post("/ingestion", response_model=IngestionResponse, status_code=201)
async def create_ingestion(
    payload: IngestionPayload, client: AirbyteClient = Depends(get_airbyte_client)
) -> IngestionResponse:
    """Create a connection between an existing source and sink."""

    conn_req = {
        "sourceId": payload.source_id,
        "destinationId": payload.sink_id,
        "name": f"{payload.source_id}-{payload.sink_id}",
        "syncCatalog": {"streams": []},
    }
    try:
        conn_result = await client.create_connection(conn_req)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    now = datetime.utcnow()
    created = payload.created or now
    updated = payload.updated or now
    return IngestionResponse(
        id=str(conn_result["connectionId"]),
        source_id=payload.source_id,
        sink_id=payload.sink_id,
        created=created,
        updated=updated,
    )
