"""
FastAPI Inference Service for MLflow Models.

Provides REST API endpoints for:
- Model inference (single and batch predictions)
- Health checks
- Model metadata
"""

import os
import pickle
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn


# ============================================================================
# Pydantic Models
# ============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    model_loaded: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class ModelMetadata(BaseModel):
    """Model metadata response."""

    model_name: str
    model_version: str
    mlflow_run_id: str
    loaded_at: str
    feature_names: List[str]
    model_type: str


class InferenceRequest(BaseModel):
    """Inference request schema."""

    inputs: Dict[str, List[Any]] = Field(
        ...,
        description="Dictionary of feature names to lists of values",
        example={
            "total_purchases": [10, 25, 5],
            "avg_purchase_value": [50.0, 120.5, 30.0],
            "days_since_last_purchase": [5, 15, 200],
        },
    )
    return_probabilities: bool = Field(
        default=False, description="Whether to return prediction probabilities"
    )


class InferenceResponse(BaseModel):
    """Inference response schema."""

    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None
    inference_time_ms: float
    timestamp: str
    model_name: str
    model_version: str


class BatchInferenceRequest(BaseModel):
    """Batch inference request schema."""

    instances: List[Dict[str, Any]] = Field(
        ...,
        description="List of instances to predict",
        example=[
            {"total_purchases": 10, "avg_purchase_value": 50.0},
            {"total_purchases": 25, "avg_purchase_value": 120.5},
        ],
    )
    return_probabilities: bool = False


# ============================================================================
# Model Loader
# ============================================================================


class ModelLoader:
    """Lazy model loader with caching."""

    def __init__(
        self, mlflow_tracking_uri: str, model_name: str, model_version: Optional[str] = None
    ):
        """Initialize model loader."""
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.model_name = model_name
        self.model_version = model_version or "latest"

        self.model = None
        self.model_metadata = None
        self.loaded_at = None

        mlflow.set_tracking_uri(mlflow_tracking_uri)

        print(f"✅ ModelLoader initialized")
        print(f"   MLflow URI: {mlflow_tracking_uri}")
        print(f"   Model: {model_name}")
        print(f"   Version: {self.model_version}")

    def load_model(self):
        """Load model from MLflow."""
        if self.model is not None:
            return self.model

        try:
            print(f"\n📥 Loading model from MLflow...")
            start_time = time.time()

            # Build model URI
            if self.model_version == "latest":
                model_uri = f"models:/{self.model_name}/latest"
            else:
                model_uri = f"models:/{self.model_name}/{self.model_version}"

            # Load model
            self.model = mlflow.sklearn.load_model(model_uri)

            # Get model metadata
            client = mlflow.tracking.MlflowClient()
            if self.model_version == "latest":
                versions = client.get_latest_versions(
                    self.model_name, stages=["None", "Staging", "Production"]
                )
                if versions:
                    model_version_obj = versions[0]
                else:
                    raise ValueError(f"No versions found for model {self.model_name}")
            else:
                model_version_obj = client.get_model_version(self.model_name, self.model_version)

            # Get run details
            run = client.get_run(model_version_obj.run_id)

            self.model_metadata = {
                "model_name": self.model_name,
                "model_version": model_version_obj.version,
                "mlflow_run_id": model_version_obj.run_id,
                "loaded_at": datetime.now().isoformat(),
                "feature_names": (
                    list(self.model.feature_names_in_)
                    if hasattr(self.model, "feature_names_in_")
                    else []
                ),
                "model_type": type(self.model).__name__,
            }

            self.loaded_at = datetime.now().isoformat()
            load_time = (time.time() - start_time) * 1000

            print(f"   ✅ Model loaded in {load_time:.2f}ms")
            print(f"   Model type: {self.model_metadata['model_type']}")
            print(f"   Version: {self.model_metadata['model_version']}")
            print(f"   Run ID: {self.model_metadata['mlflow_run_id']}")

            return self.model

        except Exception as e:
            print(f"   ❌ Failed to load model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    def predict(self, X: pd.DataFrame, return_probabilities: bool = False) -> Dict:
        """Make predictions."""
        model = self.load_model()

        start_time = time.time()

        try:
            # Make predictions
            predictions = model.predict(X)

            # Get probabilities if requested
            probabilities = None
            if return_probabilities and hasattr(model, "predict_proba"):
                probabilities = model.predict_proba(X).tolist()

            inference_time_ms = (time.time() - start_time) * 1000

            return {
                "predictions": (
                    predictions.tolist() if isinstance(predictions, np.ndarray) else predictions
                ),
                "probabilities": probabilities,
                "inference_time_ms": round(inference_time_ms, 2),
                "timestamp": datetime.now().isoformat(),
                "model_name": self.model_name,
                "model_version": self.model_metadata["model_version"],
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ============================================================================
# FastAPI Application
# ============================================================================


# Environment configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-service:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "churn_predictor_feast")
MODEL_VERSION = os.getenv("MODEL_VERSION", "latest")

# Initialize app
app = FastAPI(
    title="ML Model Inference Service",
    description="Production ML model serving with MLflow",
    version="1.0.0",
)

# Initialize model loader (lazy loading)
model_loader = ModelLoader(
    mlflow_tracking_uri=MLFLOW_TRACKING_URI, model_name=MODEL_NAME, model_version=MODEL_VERSION
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": "ML Model Inference Service",
        "version": "1.0.0",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "endpoints": {
            "health": "/health",
            "metadata": "/metadata",
            "predict": "/predict",
            "batch_predict": "/batch_predict",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model_loader.model is not None,
        "model_name": MODEL_NAME if model_loader.model is not None else None,
        "model_version": (
            model_loader.model_metadata.get("model_version")
            if model_loader.model_metadata
            else None
        ),
    }


@app.get("/metadata", response_model=ModelMetadata, tags=["Model"])
async def get_metadata():
    """Get model metadata."""
    # Ensure model is loaded
    model_loader.load_model()

    if not model_loader.model_metadata:
        raise HTTPException(status_code=500, detail="Model metadata not available")

    return model_loader.model_metadata


@app.post("/predict", response_model=InferenceResponse, tags=["Inference"])
async def predict(request: InferenceRequest):
    """
    Make predictions on input data.

    Example request:
    ```json
    {
      "inputs": {
        "total_purchases": [10, 25, 5],
        "avg_purchase_value": [50.0, 120.5, 30.0],
        "days_since_last_purchase": [5, 15, 200],
        "customer_lifetime_value": [500.0, 3000.0, 150.0],
        "account_age_days": [365, 730, 180],
        "support_tickets_count": [2, 1, 8]
      },
      "return_probabilities": true
    }
    ```
    """
    try:
        # Convert inputs to DataFrame
        df = pd.DataFrame(request.inputs)

        # Make predictions
        result = model_loader.predict(df, request.return_probabilities)

        return InferenceResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")


@app.post("/batch_predict", response_model=InferenceResponse, tags=["Inference"])
async def batch_predict(request: BatchInferenceRequest):
    """
    Make batch predictions.

    Example request:
    ```json
    {
      "instances": [
        {
          "total_purchases": 10,
          "avg_purchase_value": 50.0,
          "days_since_last_purchase": 5,
          "customer_lifetime_value": 500.0,
          "account_age_days": 365,
          "support_tickets_count": 2
        },
        {
          "total_purchases": 25,
          "avg_purchase_value": 120.5,
          "days_since_last_purchase": 15,
          "customer_lifetime_value": 3000.0,
          "account_age_days": 730,
          "support_tickets_count": 1
        }
      ],
      "return_probabilities": true
    }
    ```
    """
    try:
        # Convert instances to DataFrame
        df = pd.DataFrame(request.instances)

        # Make predictions
        result = model_loader.predict(df, request.return_probabilities)

        return InferenceResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Batch prediction failed: {str(e)}")


if __name__ == "__main__":
    # Run with uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
