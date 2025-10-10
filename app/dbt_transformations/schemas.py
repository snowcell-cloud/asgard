"""
Pydantic schemas for DBT Transformations API.

This module defines all request/response models and validation logic
for the dbt transformations endpoints.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class MaterializationType(str, Enum):
    """Supported dbt materialization types for gold layer tables."""

    TABLE = "table"
    VIEW = "view"
    INCREMENTAL = "incremental"


class TransformationStatus(str, Enum):
    """Status of a dbt transformation execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DBTTransformationRequest(BaseModel):
    """Request model for creating a new dbt transformation."""

    name: str = Field(
        ...,
        description="Name of the transformation (will be used as model name)",
        min_length=1,
        max_length=100,
        pattern="^[a-zA-Z][a-zA-Z0-9_]*$",
    )

    sql_query: str = Field(
        ..., description="SQL query to transform silver layer data to gold layer", min_length=10
    )

    description: Optional[str] = Field(
        None, description="Description of what this transformation does", max_length=500
    )

    materialization: MaterializationType = Field(
        MaterializationType.TABLE,
        description="How the model should be materialized in the gold layer",
    )

    tags: Optional[List[str]] = Field(
        default_factory=list, description="Tags for categorizing and organizing transformations"
    )

    owner: Optional[str] = Field(
        "dbt", description="Owner/creator of this transformation", max_length=100
    )

    incremental_strategy: Optional[str] = Field(
        "append",
        description="Strategy for incremental models (merge, append, delete+insert)",
        pattern="^(merge|append|delete_insert)$",
    )

    unique_key: Optional[List[str]] = Field(
        None, description="Unique key columns for incremental models"
    )

    @validator("sql_query")
    def validate_sql_query(cls, v):
        """Validate SQL query for security and basic syntax."""
        if not v.strip():
            raise ValueError("SQL query cannot be empty")

        # Basic SQL injection protection
        dangerous_keywords = [
            "drop",
            "delete",
            "truncate",
            "alter",
            "create",
            "grant",
            "revoke",
            "exec",
            "execute",
            "xp_",
            "sp_",
            "insert",
            "update",
        ]

        query_lower = v.lower()
        for keyword in dangerous_keywords:
            if f" {keyword} " in query_lower or query_lower.startswith(f"{keyword} "):
                raise ValueError(f"SQL query contains potentially dangerous keyword: {keyword}")

        # Must be a SELECT statement
        if not query_lower.strip().startswith("select"):
            raise ValueError("SQL query must be a SELECT statement")

        return v

    @validator("name")
    def validate_name(cls, v):
        """Validate transformation name follows dbt naming conventions."""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Name must start with letter and contain only letters, numbers, and underscores"
            )
        return v


class DBTTransformationResponse(BaseModel):
    """Response model for dbt transformation operations."""

    transformation_id: str = Field(..., description="Unique identifier for the transformation")
    name: str = Field(..., description="Name of the transformation")
    status: TransformationStatus = Field(..., description="Current status of the transformation")
    created_at: datetime = Field(..., description="When the transformation was created")
    updated_at: datetime = Field(..., description="When the transformation was last updated")

    # Execution details
    gold_table_name: Optional[str] = Field(None, description="Name of the created gold layer table")
    row_count: Optional[int] = Field(None, description="Number of rows in the gold table")
    execution_time_seconds: Optional[float] = Field(
        None, description="Time taken to execute transformation"
    )

    # Metadata
    description: Optional[str] = Field(None, description="Transformation description")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    owner: Optional[str] = Field(None, description="Transformation owner")

    # Error details (if failed)
    error_message: Optional[str] = Field(None, description="Error message if transformation failed")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SilverLayerSource(BaseModel):
    """Model representing a silver layer data source."""

    table_name: str = Field(..., description="Name of the silver layer table")
    schema_name: str = Field(..., description="Schema containing the table")
    catalog_name: str = Field(..., description="Catalog containing the schema")

    # Table metadata
    row_count: Optional[int] = Field(None, description="Approximate number of rows")
    size_bytes: Optional[int] = Field(None, description="Table size in bytes")
    last_modified: Optional[datetime] = Field(None, description="When the table was last modified")

    # Schema information
    columns: List[Dict[str, str]] = Field(
        default_factory=list, description="List of columns with name and data type"
    )

    # S3 location
    location: Optional[str] = Field(None, description="S3 location of the table data")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GoldLayerTable(BaseModel):
    """Model representing a gold layer table."""

    table_name: str = Field(..., description="Name of the gold layer table")
    transformation_name: str = Field(
        ..., description="Name of the transformation that created this table"
    )

    # Table statistics
    row_count: int = Field(..., description="Number of rows in the table")
    size_bytes: int = Field(..., description="Table size in bytes")
    created_at: datetime = Field(..., description="When the table was created")
    last_updated: datetime = Field(..., description="When the table was last updated")

    # Iceberg table information
    location: str = Field(..., description="S3 location of the table")
    format: str = Field(default="iceberg", description="Table format (iceberg)")
    partition_spec: Optional[List[str]] = Field(None, description="Partition columns")

    # Metadata
    materialization: MaterializationType = Field(..., description="Table materialization type")
    tags: List[str] = Field(default_factory=list, description="Associated tags")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SQLValidationRequest(BaseModel):
    """Request model for SQL query validation."""

    sql_query: str = Field(..., description="SQL query to validate")

    @validator("sql_query")
    def validate_sql_query(cls, v):
        """Apply same validation as DBTTransformationRequest."""
        return DBTTransformationRequest.validate_sql_query(v)


class SQLValidationResponse(BaseModel):
    """Response model for SQL query validation."""

    is_valid: bool = Field(..., description="Whether the SQL query is valid")
    message: str = Field(..., description="Validation result message")
    suggested_tables: Optional[List[str]] = Field(
        None, description="Suggested silver layer tables based on query analysis"
    )


class TransformationListResponse(BaseModel):
    """Response model for listing transformations."""

    transformations: List[DBTTransformationResponse] = Field(
        ..., description="List of transformations"
    )
    total_count: int = Field(..., description="Total number of transformations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")


class SilverLayerListResponse(BaseModel):
    """Response model for listing silver layer sources."""

    sources: List[SilverLayerSource] = Field(..., description="List of silver layer sources")
    total_count: int = Field(..., description="Total number of sources")


class GoldLayerListResponse(BaseModel):
    """Response model for listing gold layer tables."""

    tables: List[GoldLayerTable] = Field(..., description="List of gold layer tables")
    total_count: int = Field(..., description="Total number of tables")
