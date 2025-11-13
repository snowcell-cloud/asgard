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
    🚀 **SINGLE-CLICK DEPLOYMENT**: Complete ML Deployment in One API Call

    **This endpoint waits for complete deployment and returns the inference URL!**

    **Workflow (all automatic):**
    1. ✅ Train model using provided Python script
    2. ✅ Build optimized Docker image (multi-stage)
    3. ✅ Push image to AWS ECR
    4. ✅ Deploy to Kubernetes with LoadBalancer
    5. ✅ Wait for external IP assignment
    6. ✅ **Return inference URL immediately** 🎯

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

    **Response (after complete deployment):**
    ```json
    {
      "model_name": "customer_churn_model",
      "experiment_name": "production_experiment",
      "status": "deployed",
      "inference_url": "http://51.89.136.142",
      "external_ip": "51.89.136.142",
      "model_version": "1",
      "run_id": "abc123def456",
      "ecr_image": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model:customer-churn-model-v1",
      "endpoints": {
        "health": "http://51.89.136.142/health",
        "metadata": "http://51.89.136.142/metadata",
        "predict": "http://51.89.136.142/predict",
        "root": "http://51.89.136.142"
      },
      "deployment_time_seconds": 245.3,
      "message": "Model deployed successfully! Use http://51.89.136.142/predict for inference"
    }
    ```

    **🎯 IMMEDIATE NEXT STEPS:**
    
    Once you get the response, your model is ready! Use the `inference_url`:
    
    **1. Health Check**
    ```bash
    curl http://51.89.136.142/health
    ```
    
    **2. Make Predictions** ⭐
    ```bash
    curl -X POST http://51.89.136.142/predict \\
      -H "Content-Type: application/json" \\
      -d '{
        "inputs": {
          "feature1": [1, 2, 3],
          "feature2": [4, 5, 6]
        }
      }'
    ```
    Response: `{"predictions": [0, 1, 1]}`
    
    **3. Get Metadata**
    ```bash
    curl http://51.89.136.142/metadata
    ```

    **⚠️ IMPORTANT NOTES:**
    - This is a **synchronous** operation (waits for completion)
    - Average deployment time: **3-5 minutes**
    - Request may take several minutes to complete
    - Set appropriate timeout on client side (600+ seconds recommended)
    - No need to poll for status - response contains everything!
    - Inference URL is returned directly in the response
    
    **💡 TIPS:**
    - Save the `inference_url` for future predictions
    - Use `endpoints.predict` for making predictions
    - Each model gets its own dedicated URL
    - Models scale independently with K8s replicas
    - Health checks available at `endpoints.health`

    **Script Requirements:**
    - Must use `mlflow.start_run()` to create a run
    - Must call `mlflow.sklearn.log_model()` to save the model
    - Can use any ML framework (sklearn, xgboost, tensorflow, etc.)
    """
    return await service.deploy_model_end_to_end(request)


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
