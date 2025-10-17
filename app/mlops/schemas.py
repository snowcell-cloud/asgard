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
# Model Training Schemas (/models)
# ============================================================================


class ModelFramework(str, Enum):
    """Supported ML frameworks."""

    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    CUSTOM = "custom"


class ModelType(str, Enum):
    """Model type classification."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    RANKING = "ranking"
    CUSTOM = "custom"


class TrainingDataSource(BaseModel):
    """Configuration for training data."""

    feature_service: Optional[str] = Field(None, description="Feast feature service name")
    feature_views: Optional[List[str]] = Field(None, description="List of Feast feature views")
    entities: Dict[str, List[Any]] = Field(..., description="Entity values for feature retrieval")
    target_column: str = Field(..., description="Target variable column name")
    event_timestamp: Optional[str] = Field(
        None, description="Event timestamp for point-in-time features"
    )


class ModelHyperparameters(BaseModel):
    """Model hyperparameters."""

    params: Dict[str, Any] = Field(default_factory=dict, description="Model parameters")


class TrainModelRequest(BaseModel):
    """Request to train a new model."""

    experiment_name: str = Field(..., description="MLflow experiment name")
    model_name: str = Field(..., description="Model name for registry")
    framework: ModelFramework = Field(..., description="ML framework to use")
    model_type: ModelType = Field(..., description="Type of ML model")
    data_source: TrainingDataSource = Field(..., description="Training data configuration")
    hyperparameters: ModelHyperparameters = Field(
        default_factory=ModelHyperparameters, description="Model hyperparameters"
    )
    description: Optional[str] = Field(None, description="Model description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Model tags")


class ModelMetrics(BaseModel):
    """Model performance metrics."""

    metrics: Dict[str, float] = Field(..., description="Metric name to value mapping")


class TrainModelResponse(BaseModel):
    """Response from model training."""

    run_id: str = Field(..., description="MLflow run ID")
    experiment_id: str = Field(..., description="MLflow experiment ID")
    model_name: str = Field(..., description="Model name")
    model_uri: str = Field(..., description="MLflow model URI")
    metrics: ModelMetrics = Field(..., description="Training metrics")
    artifact_uri: str = Field(..., description="S3 artifact location")
    status: str = Field(..., description="Training status")
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
# Model Serving Schemas (/serve)
# ============================================================================


class PredictionInput(BaseModel):
    """Input for model predictions."""

    model_name: str = Field(..., description="Model name to use")
    model_version: Optional[str] = Field(None, description="Model version (default: latest)")
    entities: Dict[str, List[Any]] = Field(..., description="Entity values for feature retrieval")
    features: Optional[Dict[str, Any]] = Field(
        None, description="Direct feature values (bypasses Feast)"
    )
    return_features: bool = Field(False, description="Include features in response")


class PredictionOutput(BaseModel):
    """Output from model predictions."""

    predictions: List[Any] = Field(..., description="Model predictions")
    model_name: str
    model_version: str
    run_id: str
    features: Optional[Dict[str, List[Any]]] = Field(
        None, description="Features used (if requested)"
    )
    prediction_time: datetime = Field(default_factory=datetime.utcnow)


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""

    model_name: str = Field(..., description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")
    feature_service: Optional[str] = Field(None, description="Feast feature service")
    feature_views: Optional[List[str]] = Field(None, description="Feast feature views")
    entities_df: Dict[str, List[Any]] = Field(..., description="DataFrame of entities as dict")
    output_path: Optional[str] = Field(None, description="S3 path for output")


class BatchPredictionResponse(BaseModel):
    """Response from batch predictions."""

    job_id: str = Field(..., description="Batch job identifier")
    model_name: str
    model_version: str
    status: str = Field(default="submitted", description="Job status")
    output_path: Optional[str] = Field(None, description="S3 output location")
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
# Model Monitoring Schemas
# ============================================================================


class MonitoringMetricType(str, Enum):
    """Types of monitoring metrics."""

    PREDICTION_DRIFT = "prediction_drift"
    FEATURE_DRIFT = "feature_drift"
    DATA_QUALITY = "data_quality"
    MODEL_PERFORMANCE = "model_performance"
    CUSTOM = "custom"


class MonitoringRequest(BaseModel):
    """Request to log monitoring metrics."""

    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    metric_type: MonitoringMetricType = Field(..., description="Type of monitoring metric")
    metrics: Dict[str, float] = Field(..., description="Monitoring metrics")
    reference_data: Optional[Dict[str, Any]] = Field(
        None, description="Reference data for comparison"
    )
    current_data: Optional[Dict[str, Any]] = Field(None, description="Current data being monitored")
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags")


class MonitoringResponse(BaseModel):
    """Response from monitoring logging."""

    monitoring_id: str = Field(..., description="Monitoring entry ID")
    model_name: str
    model_version: str
    metric_type: str
    metrics: Dict[str, float]
    alert_triggered: bool = Field(default=False, description="Whether alerts were triggered")
    alerts: List[str] = Field(default_factory=list, description="List of alerts")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MonitoringHistoryRequest(BaseModel):
    """Request to get monitoring history."""

    model_name: str = Field(..., description="Model name")
    model_version: Optional[str] = Field(None, description="Model version (optional)")
    metric_type: Optional[MonitoringMetricType] = Field(None, description="Filter by metric type")
    start_date: Optional[datetime] = Field(None, description="Start date for history")
    end_date: Optional[datetime] = Field(None, description="End date for history")
    limit: int = Field(100, description="Maximum number of records", ge=1, le=1000)


class MonitoringHistoryResponse(BaseModel):
    """Response with monitoring history."""

    model_name: str
    model_version: Optional[str]
    total_records: int
    records: List[MonitoringResponse]
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")
