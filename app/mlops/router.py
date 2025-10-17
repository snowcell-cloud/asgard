"""
FastAPI router for MLOps APIs.

Integrates Feast features with MLflow for complete ML lifecycle:
- /models: Train models with feature engineering
- /registry: Manage model versions and stages
- /serve: Make predictions with feature retrieval

Architecture:
  Iceberg/Trino (Data Layer)
         ↓
  Feast (Feature Store)
         ↓
  MLflow (Training & Registry)
         ↓
  Model Serving (Predictions)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.mlops.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelInfo,
    MonitoringRequest,
    MonitoringResponse,
    MonitoringHistoryRequest,
    MonitoringHistoryResponse,
    PredictionInput,
    PredictionOutput,
    RegisterModelRequest,
    RegisterModelResponse,
    TrainModelRequest,
    TrainModelResponse,
    ModelVersionInfo,
    MLOpsStatus,
)
from app.mlops.service import MLOpsService

router = APIRouter(prefix="/mlops", tags=["MLOps - ML Lifecycle"])

# Singleton service instance
_service_instance = None


def get_service() -> MLOpsService:
    """Get or create MLOps service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MLOpsService()
    return _service_instance


# ============================================================================
# Model Training Endpoints (/models)
# ============================================================================


@router.post("/models", response_model=TrainModelResponse, status_code=201)
async def train_model(
    request: TrainModelRequest,
    service: MLOpsService = Depends(get_service),
) -> TrainModelResponse:
    """
    Train a new ML model using Feast features.

    **Workflow:**
    1. Retrieve features from Feast feature store
    2. Train model with specified framework (sklearn, xgboost, lightgbm)
    3. Log experiment, parameters, and metrics to MLflow
    4. Store model artifacts in S3 via MLflow

    **Example Request:**
    ```json
    {
      "experiment_name": "customer_churn",
      "model_name": "churn_predictor",
      "framework": "sklearn",
      "model_type": "classification",
      "data_source": {
        "feature_views": ["customer_features"],
        "entities": {"customer_id": [1, 2, 3, 4, 5]},
        "target_column": "churned"
      },
      "hyperparameters": {
        "params": {
          "n_estimators": 100,
          "max_depth": 10,
          "random_state": 42
        }
      },
      "tags": {
        "team": "data-science",
        "use_case": "churn_prediction"
      }
    }
    ```

    **Response:**
    - `run_id`: MLflow run identifier
    - `model_uri`: MLflow model URI for loading
    - `metrics`: Training performance metrics
    - `artifact_uri`: S3 location of model artifacts
    """
    return await service.train_model(request)


@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    service: MLOpsService = Depends(get_service),
) -> List[ModelInfo]:
    """
    List all registered models in MLflow Model Registry.

    Returns model metadata including:
    - Model name and description
    - Latest versions and their stages
    - Creation and update timestamps
    """
    return await service.list_models()


@router.get("/models/{model_name}", response_model=ModelInfo)
async def get_model(
    model_name: str,
    service: MLOpsService = Depends(get_service),
) -> ModelInfo:
    """
    Get detailed information about a specific model.

    Includes:
    - All versions of the model
    - Current stage for each version (Staging, Production, Archived)
    - Associated metadata and tags
    """
    return await service.get_model_info(model_name)


# ============================================================================
# Model Registry Endpoints (/registry)
# ============================================================================


@router.post("/registry", response_model=RegisterModelResponse, status_code=201)
async def register_model(
    request: RegisterModelRequest,
    service: MLOpsService = Depends(get_service),
) -> RegisterModelResponse:
    """
    Register a trained model to MLflow Model Registry.

    **Workflow:**
    1. Takes a run_id from a training run
    2. Registers the model with a given name
    3. Creates a new version in the registry
    4. Model can then be promoted through stages

    **Example Request:**
    ```json
    {
      "model_name": "churn_predictor",
      "run_id": "abc123def456",
      "description": "Random Forest model trained on Q1 2025 data",
      "tags": {
        "data_version": "v1.2",
        "trained_by": "john.doe"
      }
    }
    ```

    **Use Case:**
    After training completes, register the model to make it available
    for use in batch predictions.
    """
    return await service.register_model(request)


# ============================================================================
# Model Serving Endpoints (/serve)
# ============================================================================

# NOTE: Real-time predictions currently disabled - batch predictions only
"""
@router.post("/serve", response_model=PredictionOutput)
async def predict(
    request: PredictionInput,
    service: MLOpsService = Depends(get_service),
) -> PredictionOutput:
    '''
    Make real-time predictions using a registered model.

    **Workflow:**
    1. Load model from MLflow (by version or stage)
    2. Retrieve features from Feast (or use provided features)
    3. Make predictions
    4. Return predictions with metadata

    **Example Request (with Feast features):**
    ```json
    {
      "model_name": "churn_predictor",
      "model_stage": "Production",
      "entities": {
        "customer_id": [12345, 67890]
      },
      "return_features": true
    }
    ```

    **Example Request (with direct features):**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "3",
      "features": {
        "total_orders": 45,
        "avg_order_value": 89.99,
        "days_since_last_order": 7
      }
    }
    ```

    **Response:**
    - `predictions`: Model predictions (list)
    - `model_version`: Version used for prediction
    - `features`: Features used (if requested)
    '''
    return await service.predict(request)
"""


@router.post("/serve/batch", response_model=BatchPredictionResponse, status_code=202)
async def batch_predict(
    request: BatchPredictionRequest,
    service: MLOpsService = Depends(get_service),
) -> BatchPredictionResponse:
    """
    Make batch predictions on large datasets.

    **Workflow:**
    1. Load model from MLflow
    2. Retrieve features for all entities from Feast
    3. Generate predictions for entire dataset
    4. Save results to S3 as Parquet

    **Example Request:**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "3",
      "feature_service": "customer_churn_features",
      "entities_df": {
        "customer_id": [1, 2, 3, ..., 10000]
      },
      "output_path": "s3://my-bucket/predictions/batch_2025_10_17.parquet"
    }
    ```

    **Use Case:**
    - Score entire customer base daily for churn risk
    - Generate recommendations for all users
    - Batch feature engineering + prediction pipelines
    """
    return await service.batch_predict(request)


# ============================================================================
# Model Monitoring Endpoints (/monitoring)
# ============================================================================


@router.post("/monitoring", response_model=MonitoringResponse, status_code=201)
async def log_monitoring_metrics(
    request: MonitoringRequest,
    service: MLOpsService = Depends(get_service),
) -> MonitoringResponse:
    """
    Log monitoring metrics for a deployed model.

    **Supported Metric Types:**
    - `prediction_drift`: Monitor changes in prediction distribution
    - `feature_drift`: Monitor changes in feature distribution
    - `data_quality`: Monitor data quality issues (missing values, outliers)
    - `model_performance`: Monitor model performance metrics
    - `custom`: Custom monitoring metrics

    **Example Request:**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "3",
      "metric_type": "prediction_drift",
      "metrics": {
        "drift_score": 0.15,
        "psi": 0.08,
        "js_divergence": 0.12
      },
      "reference_data": {
        "mean": 0.35,
        "std": 0.12
      },
      "current_data": {
        "mean": 0.42,
        "std": 0.15
      },
      "tags": {
        "deployment": "production",
        "region": "us-east-1"
      }
    }
    ```

    **Response:**
    - `monitoring_id`: Unique identifier for this monitoring entry
    - `alert_triggered`: Whether any alerts were triggered
    - `alerts`: List of alert messages (if any)
    - `metrics`: The logged metrics

    **Alert Thresholds:**
    - Drift metrics > 0.1 (10%)
    - Missing data > 0.05 (5%)
    - Accuracy < 0.7 (70%)
    """
    return await service.log_monitoring_metrics(request)


@router.post("/monitoring/history", response_model=MonitoringHistoryResponse)
async def get_monitoring_history(
    request: MonitoringHistoryRequest,
    service: MLOpsService = Depends(get_service),
) -> MonitoringHistoryResponse:
    """
    Get monitoring history for a model.

    **Example Request:**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "3",
      "metric_type": "prediction_drift",
      "start_date": "2025-10-01T00:00:00Z",
      "end_date": "2025-10-17T23:59:59Z",
      "limit": 100
    }
    ```

    **Response:**
    - `total_records`: Total number of monitoring records
    - `records`: List of monitoring entries (limited by request)
    - `summary`: Summary statistics including:
      - Total alerts triggered
      - Metric types logged
      - Date range of data
    """
    return await service.get_monitoring_history(request)


# ============================================================================
# Status and Health
# ============================================================================


@router.get("/status", response_model=MLOpsStatus)
async def get_status(
    service: MLOpsService = Depends(get_service),
) -> MLOpsStatus:
    """
    Get MLOps platform status.

    Returns:
    - MLflow connectivity and tracking URI
    - Feast feature store availability
    - Count of registered models
    - Count of active experiments
    - Count of feature views
    """
    return await service.get_status()


# @router.get("/health")
# async def health_check():
#     """Simple health check endpoint."""
#     return {
#         "status": "healthy",
#         "service": "mlops",
#         "endpoints": {
#             "training": "/mlops/models",
#             "registry": "/mlops/registry",
#             "batch_serving": "/mlops/serve/batch",
#             "monitoring": "/mlops/monitoring",
#         },
#         "note": "Real-time predictions disabled - batch only",
#     }
