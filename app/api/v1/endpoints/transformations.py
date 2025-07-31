"""
Transformation API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.models.transformation import (
    CustomerDataTransformation,
    TransformationCreate,
    TransformationExecuteRequest,
    TransformationExecuteResponse,
    TransformationHistory,
    TransformationList,
    TransformationResponse,
    TransformationStatus,
    TransformationType,
    TransformationUpdate,
)
from app.core.services.transformation_service import TransformationService
from app.utils.logging import get_logger
from app.api.v1.deps import get_current_user, get_transformation_service

router = APIRouter(prefix="/transformations", tags=["transformations"])
logger = get_logger(__name__)


@router.post(
    "/",
    response_model=TransformationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new transformation",
    description="Create a new data transformation definition with SQL query and configuration",
)
async def create_transformation(
    transformation: TransformationCreate,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationResponse:
    """
    Create a new transformation definition.

    **Example request:**
    ```json
    {
        "name": "Customer Data Cleanup",
        "description": "Remove columns and update customer names",
        "transformation_type": "transform",
        "query": "SELECT customer_id, UPPER(TRIM(name)) as name, email FROM bronze_data WHERE active = true",
        "column_operations": [
            {
                "name": "phone",
                "operation": "remove"
            },
            {
                "name": "name",
                "operation": "update",
                "expression": "UPPER(TRIM(name))"
            }
        ],
        "config": {
            "source_path": "/data/customers",
            "target_path": "/silver/customers_cleaned",
            "partition_columns": ["year", "month"],
            "data_format": "parquet"
        },
        "tags": ["customer", "cleanup", "pii"]
    }
    ```
    """
    try:
        logger.info(
            f"Creating transformation: {transformation.name}", user=current_user
        )
        result = await service.create_transformation(
            transformation, created_by=current_user
        )
        logger.info(f"Transformation created: {result.id}", user=current_user)
        return result
    except ValueError as e:
        logger.error(
            f"Validation error creating transformation: {str(e)}", user=current_user
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating transformation: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/",
    response_model=TransformationList,
    summary="List transformations",
    description="Retrieve a paginated list of transformation definitions with filtering options",
)
async def list_transformations(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: Optional[TransformationStatus] = Query(
        None, description="Filter by status"
    ),
    type_filter: Optional[TransformationType] = Query(
        None, description="Filter by transformation type"
    ),
    tag_filter: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationList:
    """
    List transformations with filtering and pagination.

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `size`: Items per page (default: 20, max: 100)
    - `status_filter`: Filter by transformation status
    - `type_filter`: Filter by transformation type
    - `tag_filter`: Filter by specific tag
    - `search`: Search in name and description
    """
    try:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if type_filter:
            filters["transformation_type"] = type_filter
        if tag_filter:
            filters["tag"] = tag_filter
        if search:
            filters["search"] = search

        result = await service.list_transformations(
            page=page, size=size, filters=filters
        )

        logger.info(f"Listed {len(result.items)} transformations", user=current_user)
        return result
    except Exception as e:
        logger.error(f"Error listing transformations: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{transformation_id}",
    response_model=TransformationResponse,
    summary="Get transformation by ID",
    description="Retrieve a specific transformation definition by its ID",
)
async def get_transformation(
    transformation_id: UUID,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationResponse:
    """
    Get a specific transformation by ID.
    """
    try:
        result = await service.get_transformation(transformation_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        logger.info(f"Retrieved transformation: {transformation_id}", user=current_user)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving transformation {transformation_id}: {str(e)}",
            user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.put(
    "/{transformation_id}",
    response_model=TransformationResponse,
    summary="Update transformation",
    description="Update an existing transformation definition",
)
async def update_transformation(
    transformation_id: UUID,
    transformation_update: TransformationUpdate,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationResponse:
    """
    Update an existing transformation.

    **Example request:**
    ```json
    {
        "name": "Updated Customer Data Cleanup",
        "description": "Enhanced customer data transformation",
        "query": "SELECT customer_id, UPPER(TRIM(name)) as name, LOWER(email) as email FROM bronze_data WHERE active = true AND created_date >= '2024-01-01'",
        "status": "active"
    }
    ```
    """
    try:
        # Check if transformation exists
        existing = await service.get_transformation(transformation_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        result = await service.update_transformation(
            transformation_id, transformation_update, modified_by=current_user
        )

        logger.info(f"Updated transformation: {transformation_id}", user=current_user)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            f"Validation error updating transformation: {str(e)}", user=current_user
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error updating transformation {transformation_id}: {str(e)}",
            user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete(
    "/{transformation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transformation",
    description="Delete a transformation definition (soft delete)",
)
async def delete_transformation(
    transformation_id: UUID,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
):
    """
    Delete a transformation (soft delete - marks as inactive).
    """
    try:
        # Check if transformation exists
        existing = await service.get_transformation(transformation_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        await service.delete_transformation(transformation_id, deleted_by=current_user)
        logger.info(f"Deleted transformation: {transformation_id}", user=current_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting transformation {transformation_id}: {str(e)}",
            user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/execute",
    response_model=TransformationExecuteResponse,
    summary="Execute transformation",
    description="Execute a transformation definition and start the PySpark job",
)
async def execute_transformation(
    execute_request: TransformationExecuteRequest,
    background_tasks: BackgroundTasks,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationExecuteResponse:
    """
    Execute a transformation definition.

    **Example request:**
    ```json
    {
        "transformation_id": "123e4567-e89b-12d3-a456-426614174000",
        "execution_config": {
            "engine": "glue",
            "worker_type": "G.1X",
            "number_of_workers": 5
        },
        "dry_run": false,
        "sample_size": 1000
    }
    ```
    """
    try:
        # Get transformation definition
        transformation = await service.get_transformation(
            execute_request.transformation_id
        )
        if not transformation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {execute_request.transformation_id} not found",
            )

        if transformation.status != TransformationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot execute transformation with status: {transformation.status}",
            )

        # Execute the transformation
        result = await service.execute_transformation(
            execute_request, transformation, background_tasks, executed_by=current_user
        )

        logger.info(
            f"Transformation execution started: {result.execution_id}",
            transformation_id=str(execute_request.transformation_id),
            user=current_user,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            f"Validation error executing transformation: {str(e)}", user=current_user
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing transformation: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/{transformation_id}/history",
    response_model=List[TransformationHistory],
    summary="Get transformation execution history",
    description="Retrieve the execution history for a specific transformation",
)
async def get_transformation_history(
    transformation_id: UUID,
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of executions to return"
    ),
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> List[TransformationHistory]:
    """
    Get execution history for a transformation.
    """
    try:
        # Check if transformation exists
        transformation = await service.get_transformation(transformation_id)
        if not transformation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        history = await service.get_transformation_history(
            transformation_id, limit=limit
        )
        logger.info(
            f"Retrieved {len(history)} history records for transformation: {transformation_id}",
            user=current_user,
        )

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving transformation history: {str(e)}", user=current_user
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/{transformation_id}/duplicate",
    response_model=TransformationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate transformation",
    description="Create a copy of an existing transformation",
)
async def duplicate_transformation(
    transformation_id: UUID,
    new_name: str = Query(..., description="Name for the duplicated transformation"),
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationResponse:
    """
    Create a duplicate of an existing transformation.
    """
    try:
        # Check if transformation exists
        original = await service.get_transformation(transformation_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        result = await service.duplicate_transformation(
            transformation_id, new_name, created_by=current_user
        )

        logger.info(
            f"Duplicated transformation: {transformation_id} -> {result.id}",
            user=current_user,
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            f"Validation error duplicating transformation: {str(e)}", user=current_user
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error duplicating transformation: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/{transformation_id}/validate",
    summary="Validate transformation",
    description="Validate a transformation query without executing it",
)
async def validate_transformation(
    transformation_id: UUID,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> JSONResponse:
    """
    Validate a transformation query syntax and logic.
    """
    try:
        transformation = await service.get_transformation(transformation_id)
        if not transformation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        validation_result = await service.validate_transformation(transformation)

        logger.info(f"Validated transformation: {transformation_id}", user=current_user)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "transformation_id": str(transformation_id),
                "is_valid": validation_result["is_valid"],
                "errors": validation_result.get("errors", []),
                "warnings": validation_result.get("warnings", []),
                "estimated_cost": validation_result.get("estimated_cost"),
                "estimated_runtime": validation_result.get("estimated_runtime"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating transformation: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Customer-specific transformation endpoints
@router.post(
    "/customer",
    response_model=TransformationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer data transformation",
    description="Create a specialized transformation for customer data with PII handling",
)
async def create_customer_transformation(
    customer_transform: CustomerDataTransformation,
    base_transformation: TransformationCreate,
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> TransformationResponse:
    """
    Create a customer-specific transformation with PII handling.

    **Example request:**
    ```json
    {
        "base_transformation": {
            "name": "Customer PII Cleanup",
            "transformation_type": "transform",
            "query": "SELECT customer_id, name, email FROM bronze_data",
            "config": {
                "source_path": "/data/customers",
                "target_path": "/silver/customers_safe"
            }
        },
        "customer_fields": ["customer_id", "name", "email", "phone"],
        "pii_handling": "mask",
        "data_retention_days": 365,
        "anonymization_rules": [
            {"field": "email", "method": "domain_mask"},
            {"field": "phone", "method": "partial_mask"}
        ]
    }
    ```
    """
    try:
        result = await service.create_customer_transformation(
            base_transformation, customer_transform, created_by=current_user
        )

        logger.info(f"Created customer transformation: {result.id}", user=current_user)
        return result

    except ValueError as e:
        logger.error(
            f"Validation error creating customer transformation: {str(e)}",
            user=current_user,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error creating customer transformation: {str(e)}", user=current_user
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/templates/customer",
    summary="Get customer transformation templates",
    description="Get predefined templates for common customer data transformations",
)
async def get_customer_templates(
    current_user: str = Depends(get_current_user),
) -> JSONResponse:
    """
    Get predefined customer transformation templates.
    """
    templates = {
        "data_cleanup": {
            "name": "Customer Data Cleanup",
            "description": "Standard customer data cleaning and validation",
            "query": """
                SELECT 
                    customer_id,
                    UPPER(TRIM(first_name)) as first_name,
                    UPPER(TRIM(last_name)) as last_name,
                    LOWER(TRIM(email)) as email,
                    REGEXP_REPLACE(phone, '[^0-9]', '') as phone,
                    CASE 
                        WHEN age BETWEEN 18 AND 120 THEN age 
                        ELSE NULL 
                    END as age,
                    COALESCE(city, 'Unknown') as city,
                    COALESCE(state, 'Unknown') as state
                FROM bronze_data 
                WHERE customer_id IS NOT NULL
                    AND LENGTH(TRIM(COALESCE(first_name, ''))) > 0
            """,
            "column_operations": [
                {
                    "name": "first_name",
                    "operation": "update",
                    "expression": "UPPER(TRIM(first_name))",
                },
                {
                    "name": "last_name",
                    "operation": "update",
                    "expression": "UPPER(TRIM(last_name))",
                },
                {
                    "name": "email",
                    "operation": "update",
                    "expression": "LOWER(TRIM(email))",
                },
                {
                    "name": "phone",
                    "operation": "update",
                    "expression": "REGEXP_REPLACE(phone, '[^0-9]', '')",
                },
            ],
        },
        "pii_anonymization": {
            "name": "Customer PII Anonymization",
            "description": "Anonymize customer PII data for analytics",
            "query": """
                SELECT 
                    customer_id,
                    CONCAT('CUSTOMER_', ROW_NUMBER() OVER (ORDER BY customer_id)) as anonymous_id,
                    CASE 
                        WHEN age < 25 THEN '18-24'
                        WHEN age < 35 THEN '25-34'
                        WHEN age < 45 THEN '35-44'
                        WHEN age < 55 THEN '45-54'
                        WHEN age < 65 THEN '55-64'
                        ELSE '65+'
                    END as age_group,
                    LEFT(postal_code, 3) as postal_area,
                    registration_date,
                    last_login_date
                FROM bronze_data 
                WHERE customer_id IS NOT NULL
            """,
            "column_operations": [
                {"name": "first_name", "operation": "remove"},
                {"name": "last_name", "operation": "remove"},
                {"name": "email", "operation": "remove"},
                {"name": "phone", "operation": "remove"},
                {
                    "name": "anonymous_id",
                    "operation": "add",
                    "expression": "CONCAT('CUSTOMER_', ROW_NUMBER() OVER (ORDER BY customer_id))",
                },
            ],
        },
        "customer_segmentation": {
            "name": "Customer Segmentation",
            "description": "Segment customers based on behavior and demographics",
            "query": """
                SELECT 
                    customer_id,
                    first_name,
                    last_name,
                    email,
                    CASE 
                        WHEN total_orders >= 50 AND total_spent >= 5000 THEN 'VIP'
                        WHEN total_orders >= 20 AND total_spent >= 2000 THEN 'Premium'
                        WHEN total_orders >= 5 AND total_spent >= 500 THEN 'Regular'
                        ELSE 'New'
                    END as customer_segment,
                    CASE 
                        WHEN DATEDIFF(CURRENT_DATE(), last_order_date) <= 30 THEN 'Active'
                        WHEN DATEDIFF(CURRENT_DATE(), last_order_date) <= 90 THEN 'At Risk'
                        ELSE 'Churned'
                    END as engagement_status,
                    total_orders,
                    total_spent,
                    avg_order_value,
                    last_order_date
                FROM (
                    SELECT 
                        customer_id,
                        first_name,
                        last_name,
                        email,
                        COUNT(*) as total_orders,
                        SUM(order_amount) as total_spent,
                        AVG(order_amount) as avg_order_value,
                        MAX(order_date) as last_order_date
                    FROM bronze_data 
                    WHERE customer_id IS NOT NULL
                        AND order_date >= '2024-01-01'
                    GROUP BY customer_id, first_name, last_name, email
                ) customer_stats
            """,
            "column_operations": [
                {
                    "name": "customer_segment",
                    "operation": "add",
                    "expression": "CASE WHEN total_orders >= 50 THEN 'VIP' ELSE 'Regular' END",
                },
                {
                    "name": "engagement_status",
                    "operation": "add",
                    "expression": "CASE WHEN DATEDIFF(CURRENT_DATE(), last_order_date) <= 30 THEN 'Active' ELSE 'Inactive' END",
                },
            ],
        },
    }

    return JSONResponse(content={"templates": templates})


@router.post(
    "/{transformation_id}/preview",
    summary="Preview transformation results",
    description="Preview the results of a transformation without executing the full job",
)
async def preview_transformation(
    transformation_id: UUID,
    sample_size: int = Query(
        100, ge=1, le=1000, description="Number of sample records"
    ),
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> JSONResponse:
    """
    Preview transformation results with a small sample of data.
    """
    try:
        transformation = await service.get_transformation(transformation_id)
        if not transformation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transformation {transformation_id} not found",
            )

        preview_result = await service.preview_transformation(
            transformation, sample_size=sample_size
        )

        logger.info(
            f"Generated preview for transformation: {transformation_id}",
            user=current_user,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "transformation_id": str(transformation_id),
                "sample_size": sample_size,
                "preview_data": preview_result["data"],
                "schema": preview_result["schema"],
                "row_count": preview_result["row_count"],
                "execution_time_ms": preview_result["execution_time_ms"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/stats/summary",
    summary="Get transformation statistics",
    description="Get summary statistics for all transformations",
)
async def get_transformation_stats(
    service: TransformationService = Depends(get_transformation_service),
    current_user: str = Depends(get_current_user),
) -> JSONResponse:
    """
    Get summary statistics for transformations.
    """
    try:
        stats = await service.get_transformation_stats()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "total_transformations": stats["total"],
                "active_transformations": stats["active"],
                "executions_last_24h": stats["executions_24h"],
                "success_rate": stats["success_rate"],
                "avg_execution_time": stats["avg_execution_time"],
                "most_used_transformations": stats["most_used"],
                "transformation_types": stats["types_breakdown"],
            },
        )

    except Exception as e:
        logger.error(f"Error getting transformation stats: {str(e)}", user=current_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
