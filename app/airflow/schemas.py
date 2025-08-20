"""Pydantic schemas for data transformation API."""

from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field, validator


class TransformationStatus(str, Enum):
    """Status of data transformation job."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DataFormat(str, Enum):
    """Supported data formats."""
    PARQUET = "parquet"
    CSV = "csv"
    JSON = "json"
    DELTA = "delta"


class S3Location(BaseModel):
    """S3 bucket and path specification."""
    bucket: str = Field(..., description="S3 bucket name")
    path: str = Field(..., description="S3 object path (prefix)")
    
    @validator('bucket')
    def validate_bucket_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Bucket name cannot be empty")
        return v.strip()
    
    @validator('path')
    def validate_path(cls, v):
        # Remove leading slash if present
        if v.startswith('/'):
            v = v[1:]
        return v


class TransformationRequest(BaseModel):
    """Request model for data transformation."""
    source: S3Location = Field(..., description="Source S3 location")
    destination: S3Location = Field(..., description="Destination S3 location")
    sql_query: str = Field(..., description="SQL query for transformation")
    
    # Optional parameters
    source_format: DataFormat = Field(default=DataFormat.PARQUET, description="Source data format")
    destination_format: DataFormat = Field(default=DataFormat.PARQUET, description="Destination data format")
    
    # Spark configuration
    spark_options: Dict[str, Any] = Field(default_factory=dict, description="Additional Spark options")
    
    # Job metadata
    job_name: Optional[str] = Field(None, description="Custom job name")
    description: Optional[str] = Field(None, description="Job description")
    
    @validator('sql_query')
    def validate_sql_query(cls, v):
        if not v or not v.strip():
            raise ValueError("SQL query cannot be empty")
        # Basic SQL injection protection - in production, use proper SQL parsing
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE']
        upper_query = v.upper()
        for keyword in dangerous_keywords:
            if keyword in upper_query:
                raise ValueError(f"SQL query contains potentially dangerous keyword: {keyword}")
        return v.strip()


class TransformationResponse(BaseModel):
    """Response model for transformation request."""
    job_id: str = Field(..., description="Unique job identifier")
    dag_run_id: str = Field(..., description="Airflow DAG run ID")
    status: TransformationStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message: str = Field(..., description="Status message")


class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str = Field(..., description="Job identifier")
    dag_run_id: str = Field(..., description="Airflow DAG run ID")
    status: TransformationStatus = Field(..., description="Current job status")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    
    # Airflow specific fields
    state: Optional[str] = Field(None, description="Airflow DAG run state")
    execution_date: Optional[datetime] = Field(None, description="DAG execution date")
    
    # Job details
    source_records: Optional[int] = Field(None, description="Number of source records processed")
    output_records: Optional[int] = Field(None, description="Number of output records generated")
    error_message: Optional[str] = Field(None, description="Error message if job failed")


class JobList(BaseModel):
    """List of jobs response."""
    jobs: List[JobStatus] = Field(..., description="List of transformation jobs")
    total: int = Field(..., description="Total number of jobs")


class SparkConfiguration(BaseModel):
    """Spark configuration options."""
    executor_memory: str = Field(default="2g", description="Executor memory")
    executor_cores: int = Field(default=2, description="Number of executor cores")
    driver_memory: str = Field(default="1g", description="Driver memory")
    max_result_size: str = Field(default="1g", description="Maximum result size")
    
    # S3 specific configurations
    s3_endpoint: Optional[str] = Field(None, description="S3 endpoint URL")
    s3_path_style_access: bool = Field(default=True, description="Use path-style S3 access")


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    airflow_status: str = Field(..., description="Airflow connection status")
    timestamp: datetime = Field(..., description="Check timestamp")
