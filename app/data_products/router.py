"""
FastAPI router for Data Product API endpoints.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime

from app.data_products.client import TrinoClient, DBTClient
from app.data_products.service import DataProductService
from app.data_products.schemas import (
    DataProductCreateRequest,
    DataProductUpdateRequest,
    DataProductMetadata,
    DataProductQueryRequest,
    DataProductQueryResponse,
    DataProductRunRequest,
    DataProductRunResponse,
    DataProductListResponse,
    DataProductType,
)


router = APIRouter(prefix="/api/v1/data-products", tags=["Data Products"])


def get_data_product_service() -> DataProductService:
    """Dependency to get DataProductService instance."""
    trino_client = TrinoClient()
    dbt_client = DBTClient()
    return DataProductService(trino_client, dbt_client)


@router.post("/", response_model=DataProductMetadata)
async def create_data_product(
    request: DataProductCreateRequest,
    service: DataProductService = Depends(get_data_product_service),
) -> DataProductMetadata:
    """
    Create a new data product.

    This endpoint creates a curated and reusable dataset by:
    1. Creating a dbt model file based on the provided SQL query
    2. Registering the data product in the registry
    3. Setting up metadata
    """
    return await service.create_data_product(request)


@router.get("/", response_model=DataProductListResponse)
async def list_data_products(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    data_product_type: Optional[DataProductType] = Query(
        None, description="Filter by data product type"
    ),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    service: DataProductService = Depends(get_data_product_service),
) -> DataProductListResponse:
    """
    List all available data products with filtering and pagination.
    """
    result = await service.list_data_products(page=page, page_size=page_size)

    # Apply filters if provided
    data_products = result["data_products"]
    if data_product_type:
        data_products = [dp for dp in data_products if dp.data_product_type == data_product_type]
    if owner:
        data_products = [dp for dp in data_products if dp.owner == owner]

    return DataProductListResponse(
        data_products=data_products, total_count=len(data_products), page=page, page_size=page_size
    )


@router.get("/{data_product_id}", response_model=DataProductMetadata)
async def get_data_product(
    data_product_id: str, service: DataProductService = Depends(get_data_product_service)
) -> DataProductMetadata:
    """
    Get details of a specific data product.
    """
    return await service.get_data_product(data_product_id)


@router.put("/{data_product_id}", response_model=DataProductMetadata)
async def update_data_product(
    data_product_id: str,
    request: DataProductUpdateRequest,
    service: DataProductService = Depends(get_data_product_service),
) -> DataProductMetadata:
    """
    Update an existing data product.
    """
    return await service.update_data_product(data_product_id, request)


@router.delete("/{data_product_id}")
async def delete_data_product(
    data_product_id: str, service: DataProductService = Depends(get_data_product_service)
) -> Dict[str, str]:
    """
    Delete a data product.
    """
    return await service.delete_data_product(data_product_id)


@router.post("/{data_product_id}/run", response_model=DataProductRunResponse)
async def run_data_product(
    data_product_id: str,
    force_rebuild: bool = Query(False, description="Force full rebuild"),
    service: DataProductService = Depends(get_data_product_service),
) -> DataProductRunResponse:
    """
    Run/refresh a data product by executing its dbt model.

    This triggers the data transformation pipeline to update the data product
    with the latest data from the silver layer.
    """
    result = await service.run_data_product(data_product_id, force_rebuild)
    return DataProductRunResponse(**result)


@router.get("/{data_product_id}/query", response_model=DataProductQueryResponse)
async def query_data_product(
    data_product_id: str,
    limit: int = Query(100, ge=1, le=10000, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    where: Optional[str] = Query(None, description="SQL WHERE clause filter"),
    service: DataProductService = Depends(get_data_product_service),
) -> DataProductQueryResponse:
    """
    Query data from a data product.

    Returns the actual data from the curated dataset with optional filtering.
    """
    result = await service.query_data_product(
        data_product_id=data_product_id, limit=limit, offset=offset, where_clause=where or ""
    )
    return DataProductQueryResponse(**result)


@router.get("/{data_product_id}/schema")
async def get_data_product_schema(
    data_product_id: str, service: DataProductService = Depends(get_data_product_service)
) -> Dict[str, Any]:
    """
    Get the schema/structure of a data product.
    """
    data_product = await service.get_data_product(data_product_id)

    # Check if table exists and get schema
    if await service.trino_client.table_exists(data_product.table_name):
        schema = await service.trino_client.get_table_schema(data_product.table_name)
        return {
            "data_product_id": data_product_id,
            "table_name": data_product.table_name,
            "schema": schema,
            "last_updated": data_product.updated_at,
        }
    else:
        return {
            "data_product_id": data_product_id,
            "table_name": data_product.table_name,
            "schema": [],
            "message": "Table not found. Run the data product first.",
            "last_updated": data_product.updated_at,
        }


@router.get("/{data_product_id}/lineage")
async def get_data_product_lineage(
    data_product_id: str, service: DataProductService = Depends(get_data_product_service)
) -> Dict[str, Any]:
    """
    Get the data lineage for a data product.

    Shows source tables, transformations, and downstream consumers.
    """
    data_product = await service.get_data_product(data_product_id)

    # This is a simplified lineage view
    # In a production system, you'd integrate with tools like dbt docs or Apache Atlas
    return {
        "data_product_id": data_product_id,
        "upstream_sources": [
            "silver.customer_data",
            "silver.transaction_data",
            "silver.product_data",
        ],
        "transformation_type": "dbt_model",
        "downstream_consumers": data_product.consumers,
        "owner": data_product.owner,
        "last_run": data_product.last_run_at,
    }


@router.get("/{data_product_id}/metrics")
async def get_data_product_metrics(
    data_product_id: str, service: DataProductService = Depends(get_data_product_service)
) -> Dict[str, Any]:
    """
    Get quality and usage metrics for a data product.
    """
    data_product = await service.get_data_product(data_product_id)

    if not await service.trino_client.table_exists(data_product.table_name):
        return {
            "data_product_id": data_product_id,
            "message": "Table not found. Run the data product first.",
        }

    # Get basic metrics
    stats_query = f"""
    SELECT 
        COUNT(*) as row_count,
        COUNT(DISTINCT data_product_owner) as unique_owners,
        MAX(data_product_updated_at) as last_update
    FROM {service.trino_client.catalog}.{service.trino_client.schema}.{data_product.table_name}
    """

    try:
        result = await service.trino_client.execute_query(stats_query)
        data = result.get("data", [[0, 0, None]])[0]

        return {
            "data_product_id": data_product_id,
            "row_count": data[0],
            "unique_owners": data[1],
            "last_data_update": data[2],
            "metadata_last_update": data_product.updated_at,
            "status": data_product.status,
            "consumers": len(data_product.consumers),
            "tags": data_product.tags,
        }
    except Exception as e:
        return {"data_product_id": data_product_id, "error": f"Failed to get metrics: {str(e)}"}
