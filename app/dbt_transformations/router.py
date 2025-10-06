"""
FastAPI router for DBT Transformations API.

This router provides endpoints for SQL-driven data transformations
from silver layer to gold layer using dbt and Trino.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from .service import DBTTransformationService
from .schemas import (
    DBTTransformationRequest,
    DBTTransformationResponse,
    TransformationListResponse,
    SilverLayerListResponse,
    GoldLayerListResponse,
    SQLValidationRequest,
    SQLValidationResponse,
    TransformationStatus,
)


router = APIRouter(
    prefix="/dbt",
    tags=["DBT Transformations"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)


def get_dbt_service() -> DBTTransformationService:
    """Dependency to get DBTTransformationService instance."""
    return DBTTransformationService()


@router.post("/transform", response_model=DBTTransformationResponse)
async def create_transformation(
    request: DBTTransformationRequest,
    background_tasks: BackgroundTasks,
    service: DBTTransformationService = Depends(get_dbt_service),
) -> DBTTransformationResponse:
    """
    Create and execute a new dbt transformation.

    This endpoint:
    1. Validates the provided SQL query
    2. Creates a dynamic dbt model
    3. Executes the transformation from silver to gold layer
    4. Returns transformation results and metadata

    **Example SQL Query:**
    ```sql
    SELECT
        customer_id,
        COUNT(*) as transaction_count,
        SUM(amount) as total_amount,
        AVG(amount) as avg_amount
    FROM silver.transaction_data
    WHERE transaction_date >= '2024-01-01'
    GROUP BY customer_id
    ```
    """
    try:
        result = await service.create_dynamic_transformation(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create transformation: {str(e)}")


@router.get("/transformations", response_model=TransformationListResponse)
async def list_transformations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[TransformationStatus] = Query(None, description="Filter by status"),
    service: DBTTransformationService = Depends(get_dbt_service),
) -> TransformationListResponse:
    """
    List all dbt transformations with pagination and filtering.

    Returns a paginated list of transformations with their current status,
    execution details, and metadata.
    """
    try:
        result = await service.list_transformations(page=page, page_size=page_size)

        # Apply status filter if provided
        if status:
            filtered_transformations = [t for t in result["transformations"] if t.status == status]
            result["transformations"] = filtered_transformations
            result["total_count"] = len(filtered_transformations)

        return TransformationListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list transformations: {str(e)}")


@router.get("/transformations/{transformation_id}", response_model=DBTTransformationResponse)
async def get_transformation(
    transformation_id: str,
    service: DBTTransformationService = Depends(get_dbt_service),
) -> DBTTransformationResponse:
    """
    Get details of a specific transformation by ID.

    Returns complete information about the transformation including
    execution status, results, and any error messages.
    """
    return await service.get_transformation(transformation_id)


@router.delete("/transformations/{transformation_id}")
async def delete_transformation(
    transformation_id: str,
    service: DBTTransformationService = Depends(get_dbt_service),
) -> Dict[str, str]:
    """
    Delete a transformation.

    This removes the transformation metadata. The gold layer table
    may optionally be preserved based on configuration.
    """
    return await service.delete_transformation(transformation_id)


@router.get("/sources/silver", response_model=SilverLayerListResponse)
async def list_silver_layer_sources(
    service: DBTTransformationService = Depends(get_dbt_service),
) -> SilverLayerListResponse:
    """
    List available silver layer data sources.

    Returns all tables available in the silver layer that can be used
    as sources for transformations, including schema information and statistics.
    """
    try:
        sources = await service.get_silver_layer_sources()
        return SilverLayerListResponse(sources=sources, total_count=len(sources))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve silver layer sources: {str(e)}"
        )


@router.get("/tables/gold", response_model=GoldLayerListResponse)
async def list_gold_layer_tables(
    service: DBTTransformationService = Depends(get_dbt_service),
) -> GoldLayerListResponse:
    """
    List all gold layer tables created by transformations.

    Returns information about all tables in the gold layer that were
    created through the transformation API, including storage details
    and access patterns.
    """
    try:
        tables = await service.get_gold_layer_tables()
        return GoldLayerListResponse(tables=tables, total_count=len(tables))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve gold layer tables: {str(e)}"
        )

