"""
Pydantic schemas for MLOps APIs.

This module defines request/response models for:
- Model training with Feast features
- Model registry management
- Model serving and predictions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# ============================================================================
# Model Registry Schemas (/registry)
# ============================================================================


class RegisterModelRequest(BaseModel):
    """Request to register a model."""

    model_name: str = Field(..., description="Model name")
    run_id: str = Field(..., description="MLflow run ID to register")
    description: Optional[str] = Field(None, description="Model version description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Model version tags")


class RegisterModelResponse(BaseModel):
    """Response from model registration."""

    model_name: str
    version: str
    run_id: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ModelVersionInfo(BaseModel):
    """Information about a model version."""

    name: str
    version: str
    stage: str
    run_id: str
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ModelInfo(BaseModel):
    """Information about a registered model."""

    name: str
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    latest_versions: List[ModelVersionInfo]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Health and Status Schemas
# ============================================================================


class MLOpsStatus(BaseModel):
    """MLOps platform status."""

    mlflow_tracking_uri: str
    mlflow_available: bool
    feast_store_available: bool
    registered_models: int
    active_experiments: int
    feature_views: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Script-based Training Schemas (/training/upload)
# ============================================================================


class TrainingScriptUploadRequest(BaseModel):
    """Request to upload and execute a training script."""

    script_name: str = Field(..., description="Name for the training script")
    script_content: str = Field(..., description="Python script content (base64 encoded)")
    experiment_name: str = Field(..., description="MLflow experiment name")
    model_name: str = Field(..., description="Model name for registration")
    requirements: Optional[List[str]] = Field(
        default_factory=list, description="Additional pip packages required"
    )
    environment_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for script execution"
    )
    timeout: int = Field(300, description="Execution timeout in seconds", ge=60, le=3600)
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags for the training run")


class TrainingScriptUploadResponse(BaseModel):
    """Response from script upload and execution."""

    job_id: str = Field(..., description="Training job identifier")
    script_name: str
    experiment_name: str
    model_name: str
    status: str = Field(..., description="Job status: queued, running, completed, failed")
    run_id: Optional[str] = Field(None, description="MLflow run ID (when completed)")
    model_version: Optional[str] = Field(None, description="Registered model version")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TrainingJobStatus(BaseModel):
    """Status of a training job."""

    job_id: str
    script_name: str
    experiment_name: str
    model_name: str
    status: str
    run_id: Optional[str] = None
    model_version: Optional[str] = None
    logs: Optional[str] = Field(None, description="Training logs")
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


# ============================================================================
# Model Inference Schemas (/inference)
# ============================================================================


class InferenceRequest(BaseModel):
    """Request for model inference."""

    model_name: str = Field(..., description="Model name")
    model_version: Optional[str] = Field(None, description="Model version (default: latest)")
    inputs: Dict[str, List[Any]] = Field(..., description="Input data as dict of features")
    return_probabilities: bool = Field(False, description="Return prediction probabilities")


class InferenceResponse(BaseModel):
    """Response from model inference."""

    model_name: str
    model_version: str
    predictions: List[Any] = Field(..., description="Model predictions")
    probabilities: Optional[List[List[float]]] = Field(
        None, description="Prediction probabilities (if requested)"
    )
    inference_time_ms: float = Field(..., description="Inference time in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# End-to-End Deployment Schemas
# ============================================================================


class DeployModelRequest(BaseModel):
    """Request for complete model deployment: train -> build -> push -> deploy."""

    script_name: str = Field(..., description="Name for the training script")
    script_content: str = Field(..., description="Python script content (base64 encoded)")
    experiment_name: str = Field(..., description="MLflow experiment name")
    model_name: str = Field(..., description="Model name for registration and deployment")
    requirements: Optional[List[str]] = Field(
        default_factory=list, description="Additional pip packages required"
    )
    environment_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for script execution"
    )
    timeout: int = Field(300, description="Training timeout in seconds", ge=60, le=3600)
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags for the training run")
    replicas: int = Field(2, description="Number of K8s replicas", ge=1, le=10)
    namespace: str = Field("asgard", description="Kubernetes namespace")


class DeployModelResponse(BaseModel):
    """Response from complete model deployment."""

    job_id: str = Field(..., description="Deployment job identifier")
    model_name: str
    experiment_name: str
    status: str = Field(..., description="Deployment status")
    deployment_url: Optional[str] = Field(None, description="Model inference URL")
    external_ip: Optional[str] = Field(None, description="LoadBalancer external IP")
    model_version: Optional[str] = Field(None, description="Deployed model version")
    run_id: Optional[str] = Field(None, description="MLflow run ID")
    ecr_image: Optional[str] = Field(None, description="ECR image URI")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
