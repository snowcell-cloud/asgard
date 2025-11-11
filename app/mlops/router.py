"""
FastAPI router for MLOps APIs.

Simplified API for script-based training and model serving:
- /training/upload: Upload Python scripts for training
- /training/jobs/{job_id}: Check training job status
- /inference: Run predictions on trained models
- /registry: Register and manage models
- /models: List registered models
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.mlops.schemas import (
    InferenceRequest,
    InferenceResponse,
    ModelInfo,
    RegisterModelRequest,
    RegisterModelResponse,
    TrainingJobStatus,
    TrainingScriptUploadRequest,
    TrainingScriptUploadResponse,
    ModelVersionInfo,
    MLOpsStatus,
    DeployModelRequest,
    DeployModelResponse,
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
# Script-based Training Endpoints (/training)
# ============================================================================


@router.post("/training/upload", response_model=TrainingScriptUploadResponse, status_code=202)
async def upload_training_script(
    request: TrainingScriptUploadRequest,
    service: MLOpsService = Depends(get_service),
) -> TrainingScriptUploadResponse:
    """
    Upload and execute a Python training script (.py file).

    **Workflow:**
    1. Upload a Python script (base64 encoded or plain text)
    2. Script is executed in isolated environment with MLflow tracking
    3. Model is automatically registered to MLflow
    4. Returns job ID for status tracking

    **Script Requirements:**
    - Must use `mlflow.start_run()` to create a run
    - Must call `mlflow.log_model()` to save the trained model
    - Can use any ML framework (sklearn, xgboost, tensorflow, etc.)

    **Example Request:**
    ```json
    {
      "script_name": "churn_model_training.py",
      "script_content": "aW1wb3J0IG1sZmxvdw...",
      "experiment_name": "customer_churn",
      "model_name": "churn_predictor",
      "requirements": ["scikit-learn", "pandas", "numpy"],
      "environment_vars": {
        "DATA_PATH": "/data/customers.csv"
      },
      "timeout": 300,
      "tags": {"version": "1.0", "team": "data-science"}
    }
    ```

    **Response:**
    - Returns immediately with job_id
    - Use GET /mlops/training/jobs/{job_id} to check status
    """
    return await service.upload_and_execute_script(request)


@router.get("/training/jobs/{job_id}", response_model=TrainingJobStatus)
async def get_training_job_status(
    job_id: str,
    service: MLOpsService = Depends(get_service),
) -> TrainingJobStatus:
    """
    Get status of a training job.

    **Returns:**
    - Job status: queued, running, completed, failed
    - MLflow run_id (when completed)
    - Registered model version (when completed)
    - Execution logs
    - Error details (if failed)
    - Duration in seconds
    """
    return await service.get_training_job_status(job_id)


# ============================================================================
# Model Inference Endpoint (/inference)
# ============================================================================


@router.post("/inference", response_model=InferenceResponse)
async def model_inference(
    request: InferenceRequest,
    service: MLOpsService = Depends(get_service),
) -> InferenceResponse:
    """
    Run inference on a deployed model.

    **Workflow:**
    1. Load model from MLflow by name and version
    2. Make predictions on provided input data
    3. Optionally return prediction probabilities

    **Example Request:**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "1",
      "inputs": {
        "total_orders": [10, 25, 5],
        "avg_order_value": [50.0, 120.5, 30.0],
        "days_since_last_order": [5, 15, 30]
      },
      "return_probabilities": true
    }
    ```

    **Response:**
    ```json
    {
      "model_name": "churn_predictor",
      "model_version": "1",
      "predictions": [0, 0, 1],
      "probabilities": [
        [0.9, 0.1],
        [0.85, 0.15],
        [0.3, 0.7]
      ],
      "inference_time_ms": 12.5,
      "timestamp": "2025-10-23T10:00:00Z"
    }
    ```

    **Notes:**
    - Input data should match the features the model was trained on
    - Probabilities only available for classification models
    - Model is cached for faster subsequent requests
    """
    return await service.inference(request)


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
    Manually register a model from a specific MLflow run.
    """
    return await service.register_model(request)


# ============================================================================
# Model Management Endpoints (/models)
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


@router.post("/deploy", status_code=202)
async def deploy_model(
    request: DeployModelRequest,
    service: MLOpsService = Depends(get_service),
):
    """
    🚀 **ONE-CLICK DEPLOYMENT**: Train → Build → Push to ECR → Deploy to K8s

    **Complete automated workflow in a single API call:**
    1. ✅ Train model using provided Python script
    2. ✅ Build optimized Docker image
    3. ✅ Push image to AWS ECR
    4. ✅ Deploy to Kubernetes with LoadBalancer
    5. ✅ Return public inference URL

    **Example Request:**
    ```json
    {
      "script_name": "train_model.py",
      "script_content": "aW1wb3J0IG1sZmxvdw...",
      "experiment_name": "production_experiment",
      "model_name": "customer_churn_model",
      "requirements": ["scikit-learn", "pandas", "numpy"],
      "environment_vars": {},
      "timeout": 300,
      "tags": {"version": "1.0"},
      "replicas": 2,
      "namespace": "asgard"
    }
    ```

    **Response:**
    ```json
    {
      "job_id": "a3b4c5d6",
      "model_name": "customer_churn_model",
      "status": "training",
      "message": "Deployment started. Use /mlops/deployments/{job_id} to check status"
    }
    ```

    **After completion (check via /mlops/deployments/{job_id}):**
    - `deployment_url`: http://<external-ip>
    - `external_ip`: LoadBalancer IP address
    - `ecr_image`: Full ECR image URI
    - `model_version`: Registered model version

    **Endpoints on deployed service:**
    - `GET /health` - Health check
    - `GET /metadata` - Model information
    - `POST /predict` - Make predictions

    **Notes:**
    - Deployment runs in background (async)
    - Uses multi-stage Docker builds for optimization
    - Automatically configures ECR credentials
    - Sets up AWS credentials for S3 access
    - Creates LoadBalancer service for external access
    """
    return await service.deploy_model_end_to_end(request)


@router.get("/deployments/{job_id}")
async def get_deployment_status(
    job_id: str,
    service: MLOpsService = Depends(get_service),
):
    """
    Get status of an end-to-end deployment job.

    **Status values:**
    - `training`: Training model
    - `building`: Building Docker image
    - `pushing`: Pushing to ECR
    - `deploying`: Deploying to Kubernetes
    - `deployed`: Successfully deployed ✅
    - `failed`: Deployment failed ❌

    **Response includes:**
    - Current status
    - Deployment URL (when ready)
    - External IP
    - Model version
    - ECR image URI
    - Error details (if failed)
    """
    return await service.get_deployment_status(job_id)


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
