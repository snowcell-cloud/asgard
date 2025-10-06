"""
DBT Transformations Package

This package provides API endpoints for SQL-driven data transformations
from silver layer to gold layer using dbt and Trino with Iceberg tables.

Key Features:
- Dynamic dbt model generation from SQL queries
- Silver layer data discovery and validation
- Gold layer table management and optimization
- Integration with Nessie catalog and S3 storage
"""

from .service import DBTTransformationService
from .schemas import (
    DBTTransformationRequest,
    DBTTransformationResponse,
    MaterializationType,
    SilverLayerSource,
    GoldLayerTable,
    TransformationStatus,
)
from .router import router

__all__ = [
    "DBTTransformationService",
    "DBTTransformationRequest",
    "DBTTransformationResponse",
    "MaterializationType",
    "SilverLayerSource",
    "GoldLayerTable",
    "TransformationStatus",
    "router",
]
