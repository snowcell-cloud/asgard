"""FastAPI routes interacting with Airbyte."""

from fastapi import APIRouter, Depends, HTTPException

from app.airbyte.client import (
    AirbyteClient,
    AirbyteClientError,
    get_airbyte_client,
)
from app.airbyte.schemas import (
    ConnectionCreateRequest,
    ConnectionCreateResponse,
    DestinationCreateRequest,
    DestinationCreateResponse,
    JobStatusResponse,
    SourceCreateRequest,
    SourceCreateResponse,
    SyncResponse,
    WorkflowCreateRequest,
    WorkflowCreateResponse,
    Workspace,
)

router = APIRouter()


@router.get("/workspaces", response_model=list[Workspace])
async def list_workspaces(
    client: AirbyteClient = Depends(get_airbyte_client),
) -> list[Workspace]:
    """Return available workspaces."""
    try:
        workspaces = await client.list_workspaces()
        return [Workspace.model_validate(ws) for ws in workspaces]
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover - unexpected
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/connections",
    response_model=ConnectionCreateResponse,
    status_code=201,
)
async def create_connection(
    payload: ConnectionCreateRequest,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> ConnectionCreateResponse:
    """Create a connection between existing source and destination."""
    try:
        result = await client.create_connection(payload.model_dump(by_alias=True))
        return ConnectionCreateResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/sources",
    response_model=SourceCreateResponse,
    status_code=201,
)
async def create_source(
    payload: SourceCreateRequest,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> SourceCreateResponse:
    """Create a new Airbyte source."""
    try:
        result = await client.create_source(payload.model_dump(by_alias=True))
        return SourceCreateResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/destinations",
    response_model=DestinationCreateResponse,
    status_code=201,
)
async def create_destination(
    payload: DestinationCreateRequest,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> DestinationCreateResponse:
    """Create a new Airbyte destination."""
    try:
        result = await client.create_destination(payload.model_dump(by_alias=True))
        return DestinationCreateResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/connections/{connection_id}/sync",
    response_model=SyncResponse,
)
async def trigger_sync(
    connection_id: str,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> SyncResponse:
    """Trigger a sync job for the given connection."""
    try:
        result = await client.trigger_sync(connection_id)
        return SyncResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> JobStatusResponse:
    """Fetch the status of a previously triggered sync job."""
    try:
        result = await client.get_job_status(job_id)
        return JobStatusResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/workflows",
    response_model=WorkflowCreateResponse,
    status_code=201,
)
async def create_workflow(
    payload: WorkflowCreateRequest,
    client: AirbyteClient = Depends(get_airbyte_client),
) -> WorkflowCreateResponse:
    """Create a source, destination, connection, and optionally trigger a sync."""
    try:
        source = await client.create_source(payload.source.model_dump(by_alias=True))
        destination = await client.create_destination(
            payload.destination.model_dump(by_alias=True)
        )
        conn_payload = payload.connection.model_dump(by_alias=True)
        conn_payload.update(
            {
                "sourceId": source["sourceId"],
                "destinationId": destination["destinationId"],
            }
        )
        connection = await client.create_connection(conn_payload)
        job_id = None
        if payload.trigger_sync:
            sync = await client.trigger_sync(str(connection["connectionId"]))
            job_id = sync.get("jobId")
        return WorkflowCreateResponse(
            source_id=source["sourceId"],
            destination_id=destination["destinationId"],
            connection_id=connection["connectionId"],
            job_id=job_id,
        )
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc
