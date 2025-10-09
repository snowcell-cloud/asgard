"""
FastAPI router for Feast Feature Store and ML Model APIs.

Endpoints:
- POST /features → Define and register feature sets
- POST /models → Train and version ML models
- POST /predictions → Request online or batch predictions
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.feast.schemas import (
    BatchPredictionRequest,
    FeatureServiceRequest,
    FeatureSetResponse,
    FeatureStoreStatus,
    FeatureViewInfo,
    FeatureViewRequest,
    ModelInfo,
    ModelTrainingRequest,
    ModelTrainingResponse,
    OnlinePredictionRequest,
    PredictionResponse,
)
from app.feast.service import FeatureStoreService

router = APIRouter(prefix="/feast", tags=["Feast Feature Store & ML"])

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
    Create and register a new feature view from gold layer table.

    This endpoint:
    1. Validates the gold layer table exists
    2. Creates entities if needed
    3. Registers feature view with Feast
    4. Enables online serving if requested

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
      "online": true,
      "description": "Customer aggregated features"
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
    """
    return await service.get_store_status()


# ============================================================================
# Model Training Endpoints
# ============================================================================


@router.post("/models", response_model=ModelTrainingResponse, status_code=201)
async def train_model(
    request: ModelTrainingRequest,
    service: FeatureStoreService = Depends(get_service),
) -> ModelTrainingResponse:
    """
    Train a new ML model using features from gold layer.

    This endpoint:
    1. Retrieves historical features from Feast
    2. Splits data into train/test sets
    3. Trains model using specified framework
    4. Evaluates and saves model
    5. Returns metrics and model version

    **Supported Frameworks:**
    - sklearn (RandomForest, Gradient Boosting)
    - xgboost
    - lightgbm
    - tensorflow
    - pytorch

    **Example Request:**
    ```json
    {
      "name": "churn_predictor",
      "framework": "sklearn",
      "model_type": "classification",
      "training_data": {
        "entity_df_source": "customers",
        "label_column": "churned",
        "event_timestamp_column": "event_date",
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z"
      },
      "hyperparameters": {
        "params": {
          "n_estimators": 100,
          "max_depth": 10,
          "random_state": 42
        }
      },
      "test_size": 0.2,
      "description": "Customer churn prediction model"
    }
    ```

    **Response includes:**
    - Model ID and version
    - Training/test metrics
    - Artifact storage location
    - Training duration
    """
    return await service.train_model(request)


@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    service: FeatureStoreService = Depends(get_service),
) -> List[ModelInfo]:
    """
    List all trained models.

    Returns:
    - Model ID, name, version
    - Framework and model type
    - Training metrics
    - Creation timestamp
    """
    return await service.list_models()


# ============================================================================
# Prediction Endpoints
# ============================================================================


@router.post("/predictions/online", response_model=PredictionResponse)
async def predict_online(
    request: OnlinePredictionRequest,
    service: FeatureStoreService = Depends(get_service),
) -> PredictionResponse:
    """
    Make real-time online prediction.

    This endpoint:
    1. Loads the specified model
    2. Retrieves online features (if configured)
    3. Makes prediction
    4. Returns prediction with optional probabilities

    **Example Request:**
    ```json
    {
      "model_id": "abc123-def456",
      "features": {
        "total_orders": 42,
        "avg_order_value": 125.50,
        "days_since_last_order": 7,
        "customer_age": 35
      },
      "include_feature_values": true
    }
    ```

    **Response:**
    ```json
    {
      "prediction_id": "xyz789",
      "model_id": "abc123-def456",
      "model_version": "20250109_120000",
      "mode": "online",
      "prediction": 0.85,
      "probabilities": {
        "class_0": 0.15,
        "class_1": 0.85
      },
      "features_used": {...},
      "created_at": "2025-01-09T12:00:00Z",
      "execution_time_seconds": 0.05,
      "status": "completed"
    }
    ```
    """
    return await service.predict_online(request)


@router.post("/predictions/batch", response_model=PredictionResponse)
async def predict_batch(
    request: BatchPredictionRequest,
    service: FeatureStoreService = Depends(get_service),
) -> PredictionResponse:
    """
    Make batch predictions on gold layer table.

    This endpoint:
    1. Loads input data from specified table
    2. Retrieves point-in-time features (if configured)
    3. Makes predictions for all rows
    4. Writes results to output table

    **Example Request:**
    ```json
    {
      "model_id": "abc123-def456",
      "input_table": "customers_to_score",
      "entity_columns": ["customer_id"],
      "feature_views": ["customer_features"],
      "output_table": "churn_predictions",
      "output_schema": "gold",
      "prediction_column_name": "churn_probability",
      "event_timestamp_column": "score_date"
    }
    ```

    **Response:**
    ```json
    {
      "prediction_id": "batch_xyz",
      "model_id": "abc123-def456",
      "model_version": "20250109_120000",
      "mode": "batch",
      "output_table": "iceberg.gold.churn_predictions",
      "num_predictions": 10000,
      "created_at": "2025-01-09T12:00:00Z",
      "execution_time_seconds": 45.2,
      "status": "completed"
    }
    ```
    """
    return await service.predict_batch(request)

 