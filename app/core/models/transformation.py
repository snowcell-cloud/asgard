"""
Transformation models for the data lake API
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class TransformationStatus(str, Enum):
    """Status of a transformation definition"""

    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class TransformationType(str, Enum):
    """Type of transformation operation"""

    SELECT = "select"
    UPDATE = "update"
    INSERT = "insert"
    DELETE = "delete"
    AGGREGATE = "aggregate"
    JOIN = "join"
    FILTER = "filter"
    TRANSFORM = "transform"


class ColumnOperation(str, Enum):
    """Column operation types"""

    ADD = "add"
    REMOVE = "remove"
    RENAME = "rename"
    UPDATE = "update"
    CAST = "cast"


class ColumnDefinition(BaseModel):
    """Definition for column operations"""

    name: str = Field(..., description="Column name")
    operation: ColumnOperation = Field(..., description="Operation to perform")
    new_name: Optional[str] = Field(
        None, description="New column name for rename operations"
    )
    data_type: Optional[str] = Field(None, description="Data type for cast operations")
    expression: Optional[str] = Field(
        None, description="SQL expression for computed columns"
    )
    default_value: Optional[Any] = Field(
        None, description="Default value for new columns"
    )

    @validator("new_name")
    def validate_new_name(cls, v, values):
        if values.get("operation") == ColumnOperation.RENAME and not v:
            raise ValueError("new_name is required for rename operations")
        return v

    @validator("data_type")
    def validate_data_type(cls, v, values):
        if values.get("operation") == ColumnOperation.CAST and not v:
            raise ValueError("data_type is required for cast operations")
        return v


class DataValidationRule(BaseModel):
    """Data validation rules"""

    column: str = Field(..., description="Column to validate")
    rule_type: str = Field(
        ..., description="Type of validation (not_null, range, regex, etc.)"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Rule parameters"
    )
    error_message: Optional[str] = Field(None, description="Custom error message")


class TransformationConfig(BaseModel):
    """Configuration for transformation execution"""

    source_path: str = Field(..., description="Source data path in S3")
    target_path: str = Field(..., description="Target data path in S3")
    partition_columns: Optional[List[str]] = Field(
        None, description="Columns to partition by"
    )
    data_format: str = Field(default="parquet", description="Output data format")
    compression: str = Field(default="snappy", description="Compression algorithm")
    overwrite_mode: str = Field(default="overwrite", description="Write mode")
    validation_rules: List[DataValidationRule] = Field(default_factory=list)


class TransformationCreate(BaseModel):
    """Model for creating a new transformation"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Transformation name"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Transformation description"
    )
    transformation_type: TransformationType = Field(
        ..., description="Type of transformation"
    )
    query: str = Field(
        ..., min_length=1, description="SQL query or transformation logic"
    )
    column_operations: List[ColumnDefinition] = Field(
        default_factory=list, description="Column operations"
    )
    config: TransformationConfig = Field(
        ..., description="Transformation configuration"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    version: str = Field(default="1.0.0", description="Transformation version")

    @validator("query")
    def validate_query(cls, v):
        """Basic SQL query validation"""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")

        # Basic validation - check for dangerous operations
        dangerous_keywords = ["DROP", "TRUNCATE", "ALTER DATABASE", "CREATE DATABASE"]
        query_upper = v.upper()

        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Dangerous SQL keyword detected: {keyword}")

        return v.strip()

    @validator("tags")
    def validate_tags(cls, v):
        """Validate tags"""
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")

        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag length cannot exceed 50 characters")

        return list(set(v))  # Remove duplicates


class TransformationUpdate(BaseModel):
    """Model for updating an existing transformation"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    query: Optional[str] = Field(None, min_length=1)
    column_operations: Optional[List[ColumnDefinition]] = None
    config: Optional[TransformationConfig] = None
    tags: Optional[List[str]] = None
    status: Optional[TransformationStatus] = None
    version: Optional[str] = None

    @validator("query")
    def validate_query(cls, v):
        if v is not None:
            return TransformationCreate.validate_query(v)
        return v


class TransformationResponse(BaseModel):
    """Response model for transformation operations"""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    transformation_type: TransformationType
    query: str
    column_operations: List[ColumnDefinition] = Field(default_factory=list)
    config: TransformationConfig
    tags: List[str] = Field(default_factory=list)
    status: TransformationStatus = Field(default=TransformationStatus.DRAFT)
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    modified_by: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class TransformationList(BaseModel):
    """Response model for listing transformations"""

    items: List[TransformationResponse]
    total: int
    page: int
    size: int
    pages: int


class TransformationExecuteRequest(BaseModel):
    """Request model for executing a transformation"""

    transformation_id: UUID = Field(
        ..., description="ID of the transformation to execute"
    )
    execution_config: Optional[Dict[str, Any]] = Field(
        None, description="Override execution configuration"
    )
    dry_run: bool = Field(
        default=False, description="Perform a dry run without actual execution"
    )
    sample_size: Optional[int] = Field(
        None, description="Number of records to process in dry run"
    )

    @validator("sample_size")
    def validate_sample_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Sample size must be positive")
        if v is not None and v > 1000000:
            raise ValueError("Sample size cannot exceed 1,000,000 records")
        return v


class TransformationExecuteResponse(BaseModel):
    """Response model for transformation execution"""

    execution_id: UUID = Field(default_factory=uuid4)
    transformation_id: UUID
    status: str = Field(default="submitted")
    message: str
    job_id: Optional[str] = None
    execution_time: Optional[datetime] = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    dry_run: bool = False
    preview_data: Optional[List[Dict[str, Any]]] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}


class CustomerDataTransformation(BaseModel):
    """Specialized model for customer data transformations"""

    customer_fields: List[str] = Field(
        default_factory=list, description="Customer-specific fields to include"
    )
    pii_handling: str = Field(
        default="mask", description="How to handle PII data (mask, encrypt, remove)"
    )
    data_retention_days: Optional[int] = Field(
        None, description="Data retention period in days"
    )
    anonymization_rules: List[Dict[str, str]] = Field(
        default_factory=list, description="Anonymization rules"
    )

    @validator("pii_handling")
    def validate_pii_handling(cls, v):
        allowed_values = ["mask", "encrypt", "remove", "keep"]
        if v not in allowed_values:
            raise ValueError(f"pii_handling must be one of: {allowed_values}")
        return v


class TransformationMetrics(BaseModel):
    """Metrics for transformation execution"""

    records_processed: int = 0
    records_output: int = 0
    execution_time_seconds: float = 0.0
    data_quality_score: Optional[float] = None
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TransformationHistory(BaseModel):
    """History of transformation executions"""

    execution_id: UUID
    transformation_id: UUID
    executed_at: datetime
    status: str
    metrics: TransformationMetrics
    error_message: Optional[str] = None
    execution_config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
