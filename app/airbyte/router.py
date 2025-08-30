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
    DataSinkListResponse,
    DataSourcePayload,
    DataSourceResponse,
    DataSourceListResponse,
    IngestionPayload,
    IngestionResponse,
    IngestionStatusResponse,
    ScheduleConfig,
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

router = APIRouter(tags=["Data Ingestion"])

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
 
@router.get("/datasource", response_model=DataSourceListResponse)
async def get_all_datasources(
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> DataSourceListResponse:
    """Get all created data sources."""
    logger.info("Fetching all created data sources")
    
    try:
        logger.debug("Step 1: Resolving workspace ID")
        workspace_id = await _resolve_workspace_id(client)
        
        logger.debug("Step 2: Fetching sources from Airbyte")
        sources = await client.list_sources(workspace_id)
        
        logger.info(f"Found {len(sources)} sources")
        
        # Transform the response to match our schema
        source_items = []
        for source in sources:
            source_items.append({
                "sourceId": source.get("sourceId", ""),
                "name": source.get("name", ""),
                "sourceName": source.get("sourceName", ""),
                "workspaceId": source.get("workspaceId", workspace_id)
            })
        
        result = DataSourceListResponse(
            sources=source_items,
            total=len(source_items)
        )
        logger.info(f"Successfully retrieved {result.total} data sources")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_all_datasources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/sink", response_model=DataSinkListResponse)
async def get_all_sinks(
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> DataSinkListResponse:
    """Get all created data sinks (destinations)."""
    logger.info("Fetching all created data sinks")
    
    try:
        logger.debug("Step 1: Resolving workspace ID")
        workspace_id = await _resolve_workspace_id(client)
        
        logger.debug("Step 2: Fetching destinations from Airbyte")
        destinations = await client.list_destinations(workspace_id)
        
        logger.info(f"Found {len(destinations)} destinations")
        
        # Transform the response to match our schema
        destination_items = []
        for destination in destinations:
            destination_items.append({
                "destinationId": destination.get("destinationId", ""),
                "name": destination.get("name", ""),
                "destinationName": destination.get("destinationName", ""),
                "workspaceId": destination.get("workspaceId", workspace_id)
            })
        
        result = DataSinkListResponse(
            destinations=destination_items,
            total=len(destination_items)
        )
        logger.info(f"Successfully retrieved {result.total} data sinks")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_all_sinks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

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
    """Create a connection between an existing source and destination."""
    logger.info(f"Creating ingestion connection: {payload.name} (Source: {payload.sourceId} -> Destination: {payload.destinationId})")

    try:
        logger.debug("Step 1: Preparing connection request")
        conn_req = {
            "sourceId": payload.sourceId,
            "destinationId": payload.destinationId,
            "name": payload.name,
            "configurations": {
                "streams": []
            }
        }
        
        # Add schedule configuration if provided
        if payload.schedule:
            conn_req["schedule"] = {
                "scheduleType": payload.schedule.scheduleType,
            }
            if payload.schedule.cronExpression:
                conn_req["schedule"]["cronExpression"] = payload.schedule.cronExpression
        
        # Add status if provided
        if payload.status:
            conn_req["status"] = payload.status
            
        logger.info(f"Connection request prepared: {payload.name}")

        logger.debug("Step 2: Calling Airbyte create_connection API")
        conn_result = await client.create_connection(conn_req)
        logger.info(f"Connection created successfully: {conn_result.get('connectionId', 'Unknown ID')}")

        result = IngestionResponse(
            connectionId=conn_result["connectionId"],
            sourceId=payload.sourceId,
            destinationId=payload.destinationId,
            name=payload.name,
            status=payload.status or "active",
            schedule=payload.schedule,
            created=datetime.utcnow(),
        )
        logger.info(f"Successfully created ingestion connection with ID: {result.connectionId}")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in create_ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/ingestion/{ingestionId}/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    ingestionId: str,
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> IngestionStatusResponse:
    """Get the status of an ingestion connection."""
    logger.info(f"Getting status for ingestion connection: {ingestionId}")

    try:
        logger.debug("Step 1: Calling Airbyte get_connection API")
        conn_details = await client.get_connection(ingestionId)
        logger.info(f"Connection details retrieved for: {ingestionId}")

        # Extract schedule information if present
        schedule = None
        if conn_details.get("schedule"):
            schedule_data = conn_details["schedule"]
            schedule = ScheduleConfig(
                scheduleType=schedule_data.get("scheduleType", "manual"),
                cronExpression=schedule_data.get("cronExpression")
            )

        result = IngestionStatusResponse(
            ingestionId=ingestionId,
            status=conn_details.get("status", "unknown"),
            lastSync=None,  # This would need to be implemented based on Airbyte's job history API
            nextSync=None,  # This would need to be calculated based on schedule
            schedule=schedule
        )
        logger.info(f"Successfully retrieved status for connection: {ingestionId}")
        return result
        
    except AirbyteClientError as e:
        logger.error(f"Airbyte API error: {e.status_code} - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in get_ingestion_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
