"""FastAPI routes for simplified Airbyte interactions."""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.airbyte.client import (
    AirbyteClient,
    AirbyteClientError,
    get_airbyte_client_dependency,
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
    get_source_definition_id,
    get_destination_definition_id,
    list_available_sources,
    list_available_destinations,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

async def _resolve_workspace_id(client: AirbyteClient, workspace_name: str | None = None) -> str:
    """Resolve workspace ID from name or get default workspace."""
    logger.info(f"Resolving workspace ID for: {workspace_name or 'default'}")
    try:
        workspaces = await client.list_workspaces()
        logger.debug(f"Found {len(workspaces)} workspaces")
        
        if not workspaces:
            logger.error("No workspaces found in Airbyte")
            raise HTTPException(status_code=404, detail="No workspaces found")
        
        if workspace_name:
            # Find workspace by name
            for ws in workspaces:
                if ws.get("name") == workspace_name:
                    workspace_id = ws.get("workspaceId")
                    logger.info(f"Found workspace '{workspace_name}' with ID: {workspace_id}")
                    return workspace_id
            logger.error(f"Workspace '{workspace_name}' not found")
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_name}' not found")
        else:
            # Use first workspace as default
            default_ws = workspaces[0]
            workspace_id = default_ws.get("workspaceId")
            logger.info(f"Using default workspace: {default_ws.get('name')} (ID: {workspace_id})")
            return workspace_id
    except Exception as e:
        logger.error(f"Error resolving workspace: {e}")
        raise

# async def _get_source_definition_id(
#     client: AirbyteClient, source_type: DataSourceType,
#     workspace_id: str
# ) -> str:
#     logger.info(f"Getting source definition ID for type: {source_type}")
    
#     try:
#         defs = await client.list_source_definitions(workspace_id)
#         logger.info(f"Found {len(defs) if defs else 0} source definitions")
        
#         for d in defs:
#             logger.debug(f"Checking definition: {d.get('name', 'Unknown')} - {d.get('sourceDefinitionId', 'No ID')}")
#             if source_type.value.lower() in d["name"].lower():
#                 definition_id = d["sourceDefinitionId"]
#                 logger.info(f"Found matching source definition: {definition_id}")
#                 return definition_id
        
#         logger.error(f"No definition found for source type: {source_type}")
#         raise HTTPException(
#             status_code=400, detail=f"unsupported source type: {source_type}"
#         )
        
#     except Exception as e:
#         logger.error(f"Error fetching source definitions: {str(e)}")
#         raise

# ---------------------------------------------------------------------------
# Public ingestion endpoints
# ---------------------------------------------------------------------------

@router.get("/sources")
async def list_sources():
    """List all available source types (optimized - no API call needed)."""
    logger.info("Fetching available sources from pre-defined list")
    return list_available_sources()

@router.get("/destinations")
async def list_destinations():
    """List all available destination types (optimized - no API call needed)."""
    logger.info("Fetching available destinations from pre-defined list")
    return list_available_destinations()

@router.post("/datasource", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    payload: DataSourcePayload, 
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> DataSourceResponse:
    """Create a source via the Airbyte API."""
    logger.info(f"Creating datasource: {payload.name} of type {payload.type}")

    try:
        logger.debug("Step 1: Resolving workspace ID")
        workspace_id = await _resolve_workspace_id(client)
        
        logger.debug("Step 2: Getting source definition ID")
        definition_id =  get_source_definition_id(  payload.type )

        logger.debug("Step 3: Preparing Airbyte request")
        req = {
            "workspaceId": workspace_id,
            "definitionId": definition_id,
            "name": payload.name,
            "configuration": payload.config.model_dump(mode="json"),
        }
        logger.info(f"Airbyte request prepared for source: {payload.name}")

        logger.debug("Step 4: Calling Airbyte create_source API")
        resp = await client.create_source(req)
        logger.info(f"Airbyte response received: {resp.get('sourceId', 'Unknown ID')}")

        result = DataSourceResponse(
            id=resp["sourceId"],
            name=payload.name,
            type=payload.type,
            config=payload.config,
        )
        logger.info(f"Successfully created datasource with ID: {result.id}")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in create_datasource: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/sink", response_model=DataSinkResponse, status_code=201)
async def create_sink(
    payload: DataSinkPayload, 
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> DataSinkResponse:
    """Create a destination via the Airbyte API."""
    logger.info(f"Creating sink: {payload.name} of type {payload.type}")

    try:
        logger.debug("Step 1: Resolving workspace ID")
        workspace_id = await _resolve_workspace_id(client)
        
        logger.debug("Step 2: Getting destination definition ID")
        definition_id = get_destination_definition_id(payload.type)

        logger.debug("Step 3: Preparing Airbyte request")
        req = {
            "workspaceId": workspace_id,
            "definitionId": definition_id,
            "name": payload.name,
            "configuration": payload.config.model_dump(mode="json"),
        }
        logger.info(f"Airbyte request prepared for destination: {payload.name}")

        logger.debug("Step 4: Calling Airbyte create_destination API")
        resp = await client.create_destination(req)
        logger.info(f"Airbyte response received: {resp.get('destinationId', 'Unknown ID')}")

        result = DataSinkResponse(
            id=resp["destinationId"],
            name=payload.name,
            type=payload.type,
            config=payload.config,
        )
        logger.info(f"Successfully created sink with ID: {result.id}")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in create_sink: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/ingestion", response_model=IngestionResponse, status_code=201)
async def create_ingestion(
    payload: IngestionPayload, 
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
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
