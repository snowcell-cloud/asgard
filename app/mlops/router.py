"""
FastAPI router for MLOps APIs.

Simplified MLOps Management:
- /deploy: Single-click deployment (train → build → push → deploy → return URL)
- /models: List registered models
- /models/{model_name}: Get model details
- /status: Platform health status

All you need is /deploy - it handles everything and returns the inference URL!
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.mlops.schemas import (
    ModelInfo,
    MLOpsStatus,
    DeployModelRequest,
    DeployModelResponse,
    DeploymentStatusResponse,
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
# End-to-End Deployment (/deploy)
# ============================================================================


@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    service: MLOpsService = Depends(get_service),
) -> List[ModelInfo]:
    """
    List all registered models in MLflow Model Registry.

    Returns model metadata including:
    - Model name and description
    - Latest versions
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
    - Associated metadata and tags
    """
    return await service.get_model_info(model_name)


# ============================================================================
# End-to-End Deployment (/deploy)
# ============================================================================


@router.post("/deploy", response_model=DeployModelResponse)
async def deploy_model(
    request: DeployModelRequest,
    service: MLOpsService = Depends(get_service),
) -> DeployModelResponse:
    """
    🚀 **ASYNC DEPLOYMENT**: Submit ML Deployment Request

    **This endpoint returns immediately with a deployment_id!**

    **Workflow:**
    1. Submit deployment request
    2. Receive `deployment_id` immediately
    3. Poll GET `/mlops/deployments/{deployment_id}` for status
    4. Get inference URL when status is "deployed"

    **Example Request:**
    ```bash
    curl -X POST http://localhost:8000/mlops/deploy \\
      -H "Content-Type: application/json" \\
      -d '{
        "script_name": "train_model.py",
        "script_content": "...",
        "experiment_name": "production_experiment",
        "model_name": "customer_churn_model",
        "requirements": ["scikit-learn", "pandas", "numpy"],
        "environment_vars": {},
        "timeout": 300,
        "tags": {"version": "1.0"},
        "replicas": 2,
        "namespace": "asgard"
      }'
    ```

    **Response (immediate):**
    ```json
    {
      "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
      "model_name": "customer_churn_model",
      "status": "submitted",
      "message": "Deployment submitted successfully. Use GET /mlops/deployments/{deployment_id} to check status."
    }
    ```

    **Check Status:**
    ```bash
    curl http://localhost:8000/mlops/deployments/550e8400-e29b-41d4-a716-446655440000
    ```

    **Script Requirements:**
    - Must use `mlflow.start_run()` to create a run
    - Must call `mlflow.sklearn.log_model()` to save the model
    - Can use any ML framework (sklearn, xgboost, tensorflow, etc.)
    """
    return await service.submit_deployment(request)


@router.get("/deployments/{deployment_id}", response_model=DeploymentStatusResponse)
async def get_deployment_status(
    deployment_id: str,
    service: MLOpsService = Depends(get_service),
) -> DeploymentStatusResponse:
    """
    📊 **GET DEPLOYMENT STATUS**: Check deployment progress and get inference URL

    **Status Values:**
    - `submitted`: Deployment request received, waiting to start
    - `running`: Deployment in progress (training/building/deploying)
    - `deployed`: Deployment completed successfully, inference URL available
    - `failed`: Deployment failed, check error field

    **Example Request:**
    ```bash
    curl http://localhost:8000/mlops/deployments/550e8400-e29b-41d4-a716-446655440000
    ```

    **Response (while running):**
    ```json
    {
      "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
      "model_name": "customer_churn_model",
      "experiment_name": "production_experiment",
      "status": "running",
      "progress": "Building Docker image...",
      "submitted_at": "2025-11-14T10:00:00",
      "started_at": "2025-11-14T10:00:05",
      "completed_at": null,
      "inference_url": null,
      "external_ip": null,
      "run_id": "abc123",
      "model_version": null,
      "ecr_image": null,
      "endpoints": null,
      "error": null
    }
    ```

    **Response (when deployed):**
    ```json
    {
      "deployment_id": "550e8400-e29b-41d4-a716-446655440000",
      "model_name": "customer_churn_model",
      "experiment_name": "production_experiment",
      "status": "deployed",
      "progress": "Deployment completed successfully",
      "submitted_at": "2025-11-14T10:00:00",
      "started_at": "2025-11-14T10:00:05",
      "completed_at": "2025-11-14T10:04:30",
      "inference_url": "http://51.89.136.142",
      "external_ip": "51.89.136.142",
      "run_id": "abc123",
      "model_version": "1",
      "ecr_image": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model:customer-churn-model-v1",
      "endpoints": {
        "health": "http://51.89.136.142/health",
        "metadata": "http://51.89.136.142/metadata",
        "predict": "http://51.89.136.142/predict"
      },
      "error": null
    }
    ```

    **Usage:**
    - Poll this endpoint every 10-30 seconds
    - When status is "deployed", use `inference_url` for predictions
    - If status is "failed", check `error` field for details
    """
    return await service.get_deployment_status(deployment_id)


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
