"""
FastAPI router for data transformation endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends

from app.data_transformation.schemas import TransformReq
from app.data_transformation.client import get_spark_client, SparkApplicationClient
from app.data_transformation.service import TransformationService
from app.airbyte.client import get_airbyte_client_dependency, AirbyteClient

router = APIRouter(tags=["Data Transformation"])


def get_transformation_service(
    spark_client: SparkApplicationClient = Depends(get_spark_client),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client_dependency)
) -> TransformationService:
    """Dependency function to get TransformationService."""
    return TransformationService(spark_client, airbyte_client)


@router.post("/transform")
async def submit_transform(
    req: TransformReq, 
    service: TransformationService = Depends(get_transformation_service)
):
    """Submit a new SQL transformation job."""
    return await service.submit_transformation(req)


@router.get("/transform/{run_id}/status")
async def get_transform_status(
    run_id: str,
    service: TransformationService = Depends(get_transformation_service)
):
    """Get the status of a transformation job."""
    return service.get_job_status(run_id)


@router.get("/transform/{run_id}/logs")
async def get_transform_logs(
    run_id: str,
    service: TransformationService = Depends(get_transformation_service)
):
    """Get logs from the transformation job driver pod."""
    return service.get_job_logs(run_id)


@router.get("/transform/{run_id}/events")
async def get_transform_events(
    run_id: str,
    service: TransformationService = Depends(get_transformation_service)
):
    """Get Kubernetes events related to the transformation job."""
    return service.get_job_events(run_id)


@router.get("/transform/{run_id}/metrics")
async def get_transform_metrics(
    run_id: str,
    service: TransformationService = Depends(get_transformation_service)
):
    """Get metrics and resource usage for the transformation job."""
    return service.get_job_metrics(run_id)


@router.get("/transform/jobs")
async def list_transform_jobs(
    service: TransformationService = Depends(get_transformation_service),
    limit: int = 20,
    status_filter: str = None
):
    """List recent transformation jobs with their status."""
    return service.list_jobs(limit=limit, status_filter=status_filter)
