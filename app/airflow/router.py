"""FastAPI router for data transformation operations."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.airflow.client import get_airflow_client, AirflowClient
from app.airflow.schemas import (
    TransformationRequest,
    TransformationResponse,
    JobStatus,
    JobList,
    TransformationStatus,
    HealthCheck
)

router = APIRouter(prefix="/transformation", tags=["Data Transformation"])

# In-memory job tracking (in production, use a database)
job_registry: Dict[str, Dict[str, Any]] = {}


@router.post("", response_model=TransformationResponse)
async def create_transformation_job(
    request: TransformationRequest,
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> TransformationResponse:
    """Create a new data transformation job."""
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    dag_run_id = f"transform_job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Prepare DAG configuration
    dag_config = {
        "job_id": job_id,
        "source_bucket": request.source.bucket,
        "source_path": request.source.path,
        "destination_bucket": request.destination.bucket,
        "destination_path": request.destination.path,
        "sql_query": request.sql_query,
        "source_format": request.source_format.value,
        "destination_format": request.destination_format.value,
        "spark_options": request.spark_options,
        "job_name": request.job_name or f"Transform Job {job_id[:8]}",
        "description": request.description or "Data transformation job"
    }
    
    try:
        # Trigger the Airflow DAG
        dag_response = await airflow_client.trigger_dag(
            dag_id="data_transformation_dag",
            conf=dag_config,
            dag_run_id=dag_run_id
        )
        
        # Store job information
        job_registry[job_id] = {
            "job_id": job_id,
            "dag_run_id": dag_run_id,
            "request": request.dict(),
            "created_at": datetime.now(),
            "status": TransformationStatus.PENDING,
            "dag_response": dag_response
        }
        
        return TransformationResponse(
            job_id=job_id,
            dag_run_id=dag_run_id,
            status=TransformationStatus.PENDING,
            created_at=datetime.now(),
            message="Transformation job submitted successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transformation job: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> JobStatus:
    """Get the status of a specific transformation job."""
    
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = job_registry[job_id]
    
    try:
        # Get status from Airflow
        dag_status = await airflow_client.get_dag_run_status(
            dag_id="data_transformation_dag",
            dag_run_id=job_info["dag_run_id"]
        )
        
        # Map Airflow state to our status
        airflow_state = dag_status.get("state", "unknown").lower()
        if airflow_state in ["running", "queued"]:
            status = TransformationStatus.RUNNING
        elif airflow_state == "success":
            status = TransformationStatus.SUCCESS
        elif airflow_state in ["failed", "upstream_failed"]:
            status = TransformationStatus.FAILED
        else:
            status = TransformationStatus.PENDING
        
        # Update job registry
        job_registry[job_id]["status"] = status
        
        return JobStatus(
            job_id=job_id,
            dag_run_id=job_info["dag_run_id"],
            status=status,
            created_at=job_info["created_at"],
            started_at=dag_status.get("start_date"),
            completed_at=dag_status.get("end_date"),
            state=dag_status.get("state"),
            execution_date=dag_status.get("execution_date")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("", response_model=JobList)
async def list_jobs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TransformationStatus] = Query(default=None)
) -> JobList:
    """List transformation jobs with pagination."""
    
    jobs = list(job_registry.values())
    
    # Filter by status if provided
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    total = len(jobs)
    jobs_page = jobs[offset:offset + limit]
    
    # Convert to JobStatus objects
    job_statuses = []
    for job in jobs_page:
        job_statuses.append(JobStatus(
            job_id=job["job_id"],
            dag_run_id=job["dag_run_id"],
            status=job["status"],
            created_at=job["created_at"]
        ))
    
    return JobList(jobs=job_statuses, total=total)


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> JSONResponse:
    """Cancel a running transformation job."""
    
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # In a real implementation, you would call Airflow's API to stop the DAG run
    # For now, we'll just mark it as cancelled in our registry
    job_registry[job_id]["status"] = TransformationStatus.FAILED
    
    return JSONResponse(
        content={"message": f"Job {job_id} cancellation requested"},
        status_code=200
    )


@router.get("/health/status", response_model=HealthCheck)
async def health_check(
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> HealthCheck:
    """Check the health of the data transformation service."""
    
    try:
        # Test Airflow connection
        await airflow_client.list_dags()
        airflow_status = "healthy"
    except Exception:
        airflow_status = "unhealthy"
    
    return HealthCheck(
        status="healthy",
        airflow_status=airflow_status,
        timestamp=datetime.now()
    )


@router.get("/dags/list")
async def list_available_dags(
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> Dict[str, Any]:
    """List available Airflow DAGs."""
    
    try:
        dags = await airflow_client.list_dags()
        return dags
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list DAGs: {str(e)}"
        )
    
    try:
        # Trigger the Airflow DAG
        dag_response = await airflow_client.trigger_dag(
            dag_id="data_transformation_dag",
            conf=dag_config,
            dag_run_id=dag_run_id
        )
        
        # Store job information
        job_registry[job_id] = {
            "job_id": job_id,
            "dag_run_id": dag_run_id,
            "request": request.dict(),
            "created_at": datetime.now(),
            "status": TransformationStatus.PENDING
        }
        
        return TransformationResponse(
            job_id=job_id,
            dag_run_id=dag_run_id,
            status=TransformationStatus.PENDING,
            created_at=datetime.now(),
            message="Transformation job submitted successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transformation job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> JobStatus:
    """Get the status of a specific transformation job."""
    
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = job_registry[job_id]
    
    try:
        # Get status from Airflow
        dag_status = await airflow_client.get_dag_run_status(
            dag_id="data_transformation_dag",
            dag_run_id=job_info["dag_run_id"]
        )
        
        # Map Airflow state to our status
        airflow_state = dag_status.get("state", "unknown").lower()
        if airflow_state in ["running", "queued"]:
            status = TransformationStatus.RUNNING
        elif airflow_state == "success":
            status = TransformationStatus.SUCCESS
        elif airflow_state in ["failed", "upstream_failed"]:
            status = TransformationStatus.FAILED
        else:
            status = TransformationStatus.PENDING
        
        # Update job registry
        job_registry[job_id]["status"] = status
        
        return JobStatus(
            job_id=job_id,
            dag_run_id=job_info["dag_run_id"],
            status=status,
            created_at=job_info["created_at"],
            started_at=dag_status.get("start_date"),
            completed_at=dag_status.get("end_date"),
            state=dag_status.get("state"),
            execution_date=dag_status.get("execution_date")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[TransformationStatus] = Query(default=None)
) -> JobList:
    """List transformation jobs with pagination."""
    
    jobs = list(job_registry.values())
    
    # Filter by status if provided
    if status:
        jobs = [job for job in jobs if job.get("status") == status]
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    total = len(jobs)
    jobs_page = jobs[offset:offset + limit]
    
    # Convert to JobStatus objects
    job_statuses = []
    for job in jobs_page:
        job_statuses.append(JobStatus(
            job_id=job["job_id"],
            dag_run_id=job["dag_run_id"],
            status=job["status"],
            created_at=job["created_at"]
        ))
    
    return JobList(jobs=job_statuses, total=total)


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> JSONResponse:
    """Cancel a running transformation job."""
    
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # In a real implementation, you would call Airflow's API to stop the DAG run
    # For now, we'll just mark it as cancelled in our registry
    job_registry[job_id]["status"] = TransformationStatus.FAILED
    
    return JSONResponse(
        content={"message": f"Job {job_id} cancellation requested"},
        status_code=200
    )


@router.get("/health", response_model=HealthCheck)
async def health_check(
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> HealthCheck:
    """Check the health of the data transformation service."""
    
    try:
        # Test Airflow connection
        await airflow_client.list_dags()
        airflow_status = "healthy"
    except Exception:
        airflow_status = "unhealthy"
    
    return HealthCheck(
        status="healthy",
        airflow_status=airflow_status,
        timestamp=datetime.now()
    )


@router.get("/dags")
async def list_available_dags(
    airflow_client: AirflowClient = Depends(get_airflow_client)
) -> Dict[str, Any]:
    """List available Airflow DAGs."""
    
    try:
        dags = await airflow_client.list_dags()
        return dags
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list DAGs: {str(e)}"
        )
