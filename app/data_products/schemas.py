"""
Schemas for Data Product API endpoints.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DataProductType(str, Enum):
    """Supported data product types."""

    CUSTOMER_360 = "CUSTOMER_360"
    PRODUCT_PERFORMANCE = "PRODUCT_PERFORMANCE"
    REVENUE_ANALYTICS = "REVENUE_ANALYTICS"
    CUSTOM = "CUSTOM"


class UpdateFrequency(str, Enum):
    """Data product update frequencies."""

    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DataProductCreateRequest(BaseModel):
    """Request to create a new data product."""

    name: str = Field(..., description="Data product name")
    description: str = Field(..., description="Data product description")
    data_product_type: DataProductType = Field(..., description="Type of data product")
    source_query: str = Field(..., description="SQL query to generate the data product")
    owner: str = Field(default="data-platform-team", description="Data product owner")
    consumers: List[str] = Field(default=[], description="List of consumer teams/users")
    update_frequency: UpdateFrequency = Field(
        default=UpdateFrequency.DAILY, description="Update frequency"
    )
    tags: List[str] = Field(default=[], description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class DataProductUpdateRequest(BaseModel):
    """Request to update an existing data product."""

    description: Optional[str] = None
    source_query: Optional[str] = None
    owner: Optional[str] = None
    consumers: Optional[List[str]] = None
    update_frequency: Optional[UpdateFrequency] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class DataProductMetadata(BaseModel):
    """Data product metadata."""

    id: str
    name: str
    description: str
    data_product_type: DataProductType
    source_query: str
    owner: str
    consumers: List[str]
    update_frequency: UpdateFrequency
    tags: List[str]
    metadata: Dict[str, Any]
    table_name: str
    schema_name: str
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    status: str = "active"


class DataProductQueryRequest(BaseModel):
    """Request to query a data product."""

    data_product_id: str = Field(..., description="Data product ID")
    query: Optional[str] = Field(None, description="Optional custom query filter")
    limit: Optional[int] = Field(100, description="Maximum number of rows to return")
    offset: Optional[int] = Field(0, description="Number of rows to skip")


class DataProductQueryResponse(BaseModel):
    """Response from data product query."""

    data_product_id: str
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int
    returned_rows: int
    query_timestamp: datetime


class DataProductRunRequest(BaseModel):
    """Request to run/refresh a data product."""

    data_product_id: str = Field(..., description="Data product ID")
    force_rebuild: bool = Field(False, description="Force full rebuild of data product")


class DataProductRunResponse(BaseModel):
    """Response from data product run."""

    data_product_id: str
    run_id: str
    status: str
    started_at: datetime
    message: str


class DataProductListResponse(BaseModel):
    """Response for listing data products."""

    data_products: List[DataProductMetadata]
    total_count: int
    page: int
    page_size: int
