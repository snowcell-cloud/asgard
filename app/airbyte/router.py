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
    JobStatusResponse,
    SyncResponse,
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
    try:
        result = await client.create_connection(payload.model_dump(by_alias=True))
        return ConnectionCreateResponse.model_validate(result)
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
    try:
        result = await client.get_job_status(job_id)
        return JobStatusResponse.model_validate(result)
    except AirbyteClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=str(exc)) from exc
