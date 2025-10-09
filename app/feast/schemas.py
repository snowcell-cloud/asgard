"""
Pydantic schemas for Feast Feature Store and ML Model APIs.

This module defines request/response models for:
- Feature set definitions and registration
- Model training and versioning
- Prediction requests and batch scoring
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# ============================================================================
# Feature Store Schemas
# ============================================================================


class FeatureValueType(str, Enum):
    """Supported feature value types in Feast."""

    INT32 = "int32"
    INT64 = "int64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"
    BYTES = "bytes"
    BOOL = "bool"
    UNIX_TIMESTAMP = "unix_timestamp"
    ARRAY_INT32 = "array_int32"
    ARRAY_INT64 = "array_int64"
    ARRAY_FLOAT32 = "array_float32"
    ARRAY_FLOAT64 = "array_float64"
    ARRAY_STRING = "array_string"


class FeatureDefinition(BaseModel):
    """Definition of a single feature."""

    name: str = Field(..., description="Feature name", pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    dtype: FeatureValueType = Field(..., description="Feature data type")
    description: Optional[str] = Field(None, description="Feature description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Feature tags/metadata")


class EntityDefinition(BaseModel):
    """Definition of an entity (join key)."""

    name: str = Field(..., description="Entity name", pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    join_keys: List[str] = Field(..., description="Column names to use as join keys", min_length=1)
    description: Optional[str] = Field(None, description="Entity description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Entity tags/metadata")


class DataSourceConfig(BaseModel):
    """Configuration for feature data source from gold layer."""

    model_config = {"populate_by_name": True}

    table_name: str = Field(..., description="Gold layer table name")
    timestamp_field: Optional[str] = Field(
        None, description="Timestamp column for point-in-time joins"
    )
    created_timestamp_column: Optional[str] = Field(None, description="Creation timestamp column")

    # Trino/Iceberg specific
    catalog: str = Field(default="iceberg", description="Catalog name")
    schema_name: str = Field(default="gold", description="Schema name", alias="schema")


class FeatureViewRequest(BaseModel):
    """Request to create a feature view."""

    name: str = Field(..., description="Feature view name", pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    entities: List[str] = Field(
        ..., description="Entity names this feature view belongs to", min_length=1
    )
    features: List[FeatureDefinition] = Field(
        ..., description="List of features in this view", min_length=1
    )
    source: DataSourceConfig = Field(..., description="Data source configuration")
    ttl_seconds: Optional[int] = Field(
        86400, description="Time-to-live in seconds (default: 24 hours)"
    )
    description: Optional[str] = Field(None, description="Feature view description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Feature view tags")
    online: bool = Field(True, description="Enable online serving")

    @validator("ttl_seconds")
    def validate_ttl(cls, v):
        if v is not None and v <= 0:
            raise ValueError("TTL must be positive")
        return v


class FeatureServiceRequest(BaseModel):
    """Request to create a feature service (logical grouping of features)."""

    name: str = Field(..., description="Feature service name", pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    feature_views: List[str] = Field(..., description="Feature view names to include", min_length=1)
    description: Optional[str] = Field(None, description="Feature service description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags")


class FeatureSetResponse(BaseModel):
    """Response after creating/updating feature set."""

    name: str
    entities: List[str]
    features: List[str]
    source_table: str
    online_enabled: bool
    created_at: datetime
    status: str = Field(description="Status: registered, materialized, failed")
    message: Optional[str] = None


# ============================================================================
# Model Training Schemas
# ============================================================================


class ModelFramework(str, Enum):
    """Supported ML frameworks."""

    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    PROPHET = "prophet"


class ModelType(str, Enum):
    """Model types."""

    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    CLUSTERING = "clustering"
    TIME_SERIES = "time_series"
    RANKING = "ranking"


class TrainingDataConfig(BaseModel):
    """Configuration for training data."""

    feature_service: Optional[str] = Field(None, description="Feature service to use")
    feature_views: Optional[List[str]] = Field(None, description="Or specific feature views")
    entity_df_source: Optional[str] = Field(None, description="Source table for entity dataframe")
    label_column: str = Field(..., description="Target/label column name")

    # Time range for historical features
    event_timestamp_column: str = Field(..., description="Event timestamp column")
    start_date: datetime = Field(..., description="Start date for training data")
    end_date: datetime = Field(..., description="End date for training data")


class HyperParameters(BaseModel):
    """Model hyperparameters."""

    params: Dict[str, Any] = Field(
        default_factory=dict, description="Framework-specific parameters"
    )


class ModelTrainingRequest(BaseModel):
    """Request to train a new model."""

    name: str = Field(..., description="Model name", pattern="^[a-zA-Z][a-zA-Z0-9_]*$")
    framework: ModelFramework = Field(..., description="ML framework to use")
    model_type: ModelType = Field(..., description="Type of model")

    training_data: TrainingDataConfig = Field(..., description="Training data configuration")
    hyperparameters: HyperParameters = Field(
        default_factory=HyperParameters, description="Model hyperparameters"
    )

    description: Optional[str] = Field(None, description="Model description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Model tags")

    # Training options
    test_size: float = Field(0.2, ge=0.0, le=0.5, description="Test set proportion")
    random_state: int = Field(42, description="Random seed")
    auto_tune: bool = Field(False, description="Enable hyperparameter tuning")


class ModelMetrics(BaseModel):
    """Model evaluation metrics."""

    train_metrics: Dict[str, float] = Field(default_factory=dict)
    test_metrics: Dict[str, float] = Field(default_factory=dict)
    validation_metrics: Optional[Dict[str, float]] = None


class ModelTrainingResponse(BaseModel):
    """Response after model training."""

    model_id: str = Field(..., description="Unique model identifier")
    name: str
    version: str
    framework: ModelFramework
    model_type: ModelType

    status: str = Field(description="Status: training, completed, failed")
    metrics: Optional[ModelMetrics] = None

    artifact_uri: Optional[str] = Field(None, description="Model artifact storage location")
    training_duration_seconds: Optional[float] = None

    created_at: datetime
    created_by: Optional[str] = None

    error_message: Optional[str] = None


# ============================================================================
# Prediction Schemas
# ============================================================================


class PredictionMode(str, Enum):
    """Prediction execution mode."""

    ONLINE = "online"
    BATCH = "batch"


class OnlinePredictionRequest(BaseModel):
    """Request for online/real-time prediction."""

    model_id: str = Field(..., description="Model ID or name:version")
    features: Dict[str, Any] = Field(..., description="Feature values for prediction")
    include_feature_values: bool = Field(False, description="Include features in response")


class BatchPredictionRequest(BaseModel):
    """Request for batch prediction/scoring."""

    model_id: str = Field(..., description="Model ID or name:version")

    # Input data source
    input_table: str = Field(..., description="Gold layer table with entity data")
    entity_columns: List[str] = Field(..., description="Entity/join key columns")

    # Feature retrieval
    feature_service: Optional[str] = Field(None, description="Feature service to use")
    feature_views: Optional[List[str]] = Field(None, description="Or specific feature views")

    # Output configuration
    output_table: str = Field(..., description="Table to write predictions")
    output_schema: str = Field(default="gold", description="Output schema")
    prediction_column_name: str = Field(
        default="prediction", description="Name for prediction column"
    )

    # Time range (for point-in-time features)
    event_timestamp_column: Optional[str] = Field(
        None, description="Timestamp column for PIT joins"
    )


class PredictionResponse(BaseModel):
    """Response from prediction request."""

    prediction_id: str
    model_id: str
    model_version: str
    mode: PredictionMode

    # Online prediction results
    prediction: Optional[Union[float, int, str, List]] = None
    probabilities: Optional[Dict[str, float]] = None
    features_used: Optional[Dict[str, Any]] = None

    # Batch prediction results
    output_table: Optional[str] = None
    num_predictions: Optional[int] = None

    created_at: datetime
    execution_time_seconds: Optional[float] = None

    status: str = Field(description="Status: completed, failed, running")
    error_message: Optional[str] = None


# ============================================================================
# List/Query Schemas
# ============================================================================


class FeatureViewInfo(BaseModel):
    """Information about a registered feature view."""

    name: str
    entities: List[str]
    features: List[Dict[str, str]]  # [{name, dtype, description}]
    online_enabled: bool
    ttl_seconds: int
    created_at: datetime


class ModelInfo(BaseModel):
    """Information about a registered model."""

    model_id: str
    name: str
    version: str
    framework: ModelFramework
    model_type: ModelType
    status: str
    created_at: datetime
    metrics: Optional[Dict[str, float]] = None


class FeatureStoreStatus(BaseModel):
    """Overall feature store status."""

    registry_type: str
    online_store_type: str
    offline_store_type: str
    num_feature_views: int
    num_entities: int
    num_feature_services: int
    feature_views: List[str]
    entities: List[str]
