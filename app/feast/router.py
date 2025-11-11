"""
FastAPI router for Feast Feature Store.

NOTE: Feature management ONLY. For ML models, use /mlops endpoints.

Data Source: Iceberg Catalog (S3 Parquet - Native Storage)
- Features are read directly from S3 Parquet files created by Iceberg
- Iceberg manages data in Parquet format with Nessie metadata
- NO data duplication: Feast reads directly from Iceberg's S3 storage
- Path format: s3://airbytedestination1/iceberg/gold/{table}/data/*.parquet

Architecture:
  Iceberg (S3 Parquet + Nessie metadata)
         ↓ (direct read)
  Feast FileSource (S3 path)
         ↓
  Feature Store (offline serving)
         ↓
  MLOps (/mlops endpoints for training & predictions)

Endpoints:
- POST /features → Define and register feature sets from Iceberg gold layer
- POST /features/service → Create feature service (grouping of feature views)
- GET /features → List all feature views
- GET /status → Get feature store status

For ML Model Training & Predictions: Use /mlops endpoints
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.feast.schemas import (
    FeatureServiceRequest,
    FeatureSetResponse,
    FeatureStoreStatus,
    FeatureViewInfo,
    FeatureViewRequest,
)
from app.feast.service import FeatureStoreService

router = APIRouter(prefix="/feast", tags=["Feast Feature Store"])

# Singleton service instance
_service_instance = None


def get_service() -> FeatureStoreService:
    """Get or create feature store service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FeatureStoreService()
    return _service_instance


# ============================================================================
# Feature Store Endpoints
# ============================================================================


@router.post("/features", response_model=FeatureSetResponse, status_code=201)
async def create_feature_view(
    request: FeatureViewRequest,
    service: FeatureStoreService = Depends(get_service),
) -> FeatureSetResponse:
    """
    Create and register a new feature view from Iceberg gold layer.

    NOTE: Online serving is currently DISABLED. Using offline store only.

    This endpoint:
    1. Queries Trino to validate the Iceberg table exists
    2. Gets S3 Parquet file path from Iceberg metadata
    3. Creates entities if needed
    4. Registers Feast FileSource pointing to S3 Parquet (direct access)
    5. NO data sync/copy - Feast reads directly from Iceberg's S3 storage

    **Example Request:**
    ```json
    {
      "name": "customer_features",
      "entities": ["customer_id"],
      "features": [
        {
          "name": "total_orders",
          "dtype": "int64",
          "description": "Total number of orders"
        },
        {
          "name": "avg_order_value",
          "dtype": "float64",
          "description": "Average order value"
        }
      ],
      "source": {
        "table_name": "customer_aggregates",
        "timestamp_field": "created_at",
        "catalog": "iceberg",
        "schema": "gold"
      },
      "ttl_seconds": 86400,
      "online": false,
      "description": "Customer aggregated features (offline only)"
    }
    ```
    """
    return await service.create_feature_view(request)


@router.post("/features/service", status_code=201)
async def create_feature_service(
    request: FeatureServiceRequest,
    service: FeatureStoreService = Depends(get_service),
):
    """
    Create a feature service (logical grouping of feature views).

    Feature services make it easy to retrieve multiple feature views together.

    **Example Request:**
    ```json
    {
      "name": "customer_ml_service",
      "feature_views": ["customer_features", "customer_behavior"],
      "description": "Features for customer ML models"
    }
    ```
    """
    return await service.create_feature_service(request)


@router.get("/features", response_model=List[FeatureViewInfo])
async def list_feature_views(
    service: FeatureStoreService = Depends(get_service),
) -> List[FeatureViewInfo]:
    """
    List all registered feature views.

    Returns details about each feature view including:
    - Name and entities
    - List of features with types
    - Online serving status
    - TTL configuration
    """
    return await service.list_feature_views()


@router.get("/status", response_model=FeatureStoreStatus)
async def get_feature_store_status(
    service: FeatureStoreService = Depends(get_service),
) -> FeatureStoreStatus:
    """
    Get overall feature store status and statistics.

    Returns:
    - Registry and store types
    - Count of feature views, entities, services
    - List of registered components

    NOTE: For ML model training and predictions, use /mlops endpoints.
    """
    return await service.get_store_status()
