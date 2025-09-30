"""
Service layer for data product operations.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from app.data_products.client import TrinoClient, DBTClient
from app.data_products.schemas import (
    DataProductCreateRequest,
    DataProductUpdateRequest,
    DataProductMetadata,
    DataProductType,
    UpdateFrequency,
)


class DataProductService:
    """Service for managing data products."""

    def __init__(self, trino_client: TrinoClient, dbt_client: DBTClient):
        self.trino_client = trino_client
        self.dbt_client = dbt_client
        self.registry_file = "/tmp/data_products_registry.json"
        self.dbt_models_dir = "/home/hac/downloads/code/asgard-dev/dbt/models/data_products"

    def _load_registry(self) -> Dict[str, DataProductMetadata]:
        """Load data product registry from file."""
        if not os.path.exists(self.registry_file):
            return {}

        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                return {k: DataProductMetadata(**v) for k, v in data.items()}
        except Exception:
            return {}

    def _save_registry(self, registry: Dict[str, DataProductMetadata]):
        """Save data product registry to file."""
        try:
            with open(self.registry_file, "w") as f:
                json.dump({k: v.dict() for k, v in registry.items()}, f, indent=2, default=str)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save registry: {str(e)}")

    def _generate_table_name(self, name: str, data_product_type: DataProductType) -> str:
        """Generate a table name for a data product."""
        sanitized_name = name.lower().replace(" ", "_").replace("-", "_")
        prefix = "dp_"
        return f"{prefix}{sanitized_name}"

    def _create_dbt_model_file(
        self, data_product_id: str, request: DataProductCreateRequest
    ) -> str:
        """Create a dbt model file for the data product."""
        table_name = self._generate_table_name(request.name, request.data_product_type)

        model_content = f"""{{{{
  config(
    materialized='table',
    description='{request.description}',
    meta={{
      data_product_type: '{request.data_product_type.value}',
      owner: '{request.owner}',
      update_frequency: '{request.update_frequency.value}',
      consumers: {json.dumps(request.consumers)},
      tags: {json.dumps(request.tags)},
      data_product_id: '{data_product_id}'
    }}
  )
}}}}

WITH source_data AS (
{request.source_query}
),

enriched_data AS (
  SELECT 
    *,
    CURRENT_TIMESTAMP as data_product_updated_at,
    '{request.owner}' as data_product_owner,
    '{request.data_product_type.value}' as data_product_type,
    '{data_product_id}' as data_product_id
  FROM source_data
)

SELECT * FROM enriched_data"""

        model_file_path = os.path.join(self.dbt_models_dir, f"{table_name}.sql")

        # Ensure directory exists
        os.makedirs(os.path.dirname(model_file_path), exist_ok=True)

        with open(model_file_path, "w") as f:
            f.write(model_content)

        return table_name

    async def create_data_product(self, request: DataProductCreateRequest) -> DataProductMetadata:
        """Create a new data product."""
        registry = self._load_registry()

        # Check if name already exists
        for dp in registry.values():
            if dp.name == request.name:
                raise HTTPException(
                    status_code=400, detail=f"Data product '{request.name}' already exists"
                )

        # Generate unique ID
        data_product_id = str(uuid.uuid4())

        # Create dbt model file
        table_name = self._create_dbt_model_file(data_product_id, request)

        # Create metadata
        metadata = DataProductMetadata(
            id=data_product_id,
            name=request.name,
            description=request.description,
            data_product_type=request.data_product_type,
            owner=request.owner,
            consumers=request.consumers,
            update_frequency=request.update_frequency,
            tags=request.tags,
            metadata=request.metadata,
            table_name=table_name,
            schema_name=self.trino_client.schema,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="created",
        )

        # Save to registry
        registry[data_product_id] = metadata
        self._save_registry(registry)

        return metadata

    async def run_data_product(
        self, data_product_id: str, force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """Run/refresh a data product."""
        registry = self._load_registry()

        if data_product_id not in registry:
            raise HTTPException(status_code=404, detail="Data product not found")

        data_product = registry[data_product_id]

        try:
            # Run dbt model
            result = await self.dbt_client.run_model(data_product.table_name)

            if result["success"]:
                # Update last run timestamp
                data_product.last_run_at = datetime.now(timezone.utc)
                data_product.status = "active"
                data_product.updated_at = datetime.now(timezone.utc)

                registry[data_product_id] = data_product
                self._save_registry(registry)

                return {
                    "data_product_id": data_product_id,
                    "run_id": str(uuid.uuid4()),
                    "status": "success",
                    "started_at": datetime.now(timezone.utc),
                    "message": "Data product refreshed successfully",
                    "dbt_output": result["stdout"],
                }
            else:
                data_product.status = "failed"
                registry[data_product_id] = data_product
                self._save_registry(registry)

                raise HTTPException(
                    status_code=500,
                    detail=f"dbt run failed: {result.get('stderr', 'Unknown error')}",
                )

        except Exception as e:
            data_product.status = "failed"
            registry[data_product_id] = data_product
            self._save_registry(registry)
            raise HTTPException(status_code=500, detail=f"Failed to run data product: {str(e)}")

    async def query_data_product(
        self, data_product_id: str, limit: int = 100, offset: int = 0, where_clause: str = ""
    ) -> Dict[str, Any]:
        """Query a data product."""
        registry = self._load_registry()

        if data_product_id not in registry:
            raise HTTPException(status_code=404, detail="Data product not found")

        data_product = registry[data_product_id]

        # Check if table exists
        if not await self.trino_client.table_exists(data_product.table_name):
            raise HTTPException(
                status_code=404,
                detail=f"Data product table '{data_product.table_name}' not found. Run the data product first.",
            )

        # Query the table
        result = await self.trino_client.query_table(
            data_product.table_name, limit=limit, offset=offset, where_clause=where_clause
        )

        return {
            "data_product_id": data_product_id,
            "columns": [col["name"] for col in result.get("columns", [])],
            "data": result.get("data", []),
            "total_rows": len(result.get("data", [])),
            "returned_rows": len(result.get("data", [])),
            "query_timestamp": datetime.now(timezone.utc),
        }

    async def list_data_products(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all data products."""
        registry = self._load_registry()

        data_products = list(registry.values())
        total_count = len(data_products)

        # Simple pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_products = data_products[start_idx:end_idx]

        return {
            "data_products": paginated_products,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        }

    async def get_data_product(self, data_product_id: str) -> DataProductMetadata:
        """Get a specific data product."""
        registry = self._load_registry()

        if data_product_id not in registry:
            raise HTTPException(status_code=404, detail="Data product not found")

        return registry[data_product_id]

    async def update_data_product(
        self, data_product_id: str, request: DataProductUpdateRequest
    ) -> DataProductMetadata:
        """Update an existing data product."""
        registry = self._load_registry()

        if data_product_id not in registry:
            raise HTTPException(status_code=404, detail="Data product not found")

        data_product = registry[data_product_id]

        # Update fields
        if request.description is not None:
            data_product.description = request.description
        if request.source_query is not None:
            # Recreate dbt model file if query changed
            model_content = f"""{{{{
  config(
    materialized='table',
    description='{data_product.description}',
    meta={{
      data_product_type: '{data_product.data_product_type.value}',
      owner: '{data_product.owner}',
      update_frequency: '{data_product.update_frequency.value}',
      consumers: {json.dumps(data_product.consumers)},
      data_product_id: '{data_product_id}'
    }}
  )
}}}}

WITH source_data AS (
{request.source_query}
),

enriched_data AS (
  SELECT 
    *,
    CURRENT_TIMESTAMP as data_product_updated_at,
    '{data_product.owner}' as data_product_owner,
    '{data_product.data_product_type.value}' as data_product_type,
    '{data_product_id}' as data_product_id
  FROM source_data
)

SELECT * FROM enriched_data"""

            model_file_path = os.path.join(self.dbt_models_dir, f"{data_product.table_name}.sql")
            with open(model_file_path, "w") as f:
                f.write(model_content)

        if request.owner is not None:
            data_product.owner = request.owner
        if request.consumers is not None:
            data_product.consumers = request.consumers
        if request.update_frequency is not None:
            data_product.update_frequency = request.update_frequency
        if request.tags is not None:
            data_product.tags = request.tags
        if request.metadata is not None:
            data_product.metadata = request.metadata

        data_product.updated_at = datetime.now(timezone.utc)

        # Save to registry
        registry[data_product_id] = data_product
        self._save_registry(registry)

        return data_product

    async def delete_data_product(self, data_product_id: str) -> Dict[str, str]:
        """Delete a data product."""
        registry = self._load_registry()

        if data_product_id not in registry:
            raise HTTPException(status_code=404, detail="Data product not found")

        data_product = registry[data_product_id]

        try:
            # Remove dbt model file
            model_file_path = os.path.join(self.dbt_models_dir, f"{data_product.table_name}.sql")
            if os.path.exists(model_file_path):
                os.remove(model_file_path)

            # Drop table if exists
            await self.trino_client.drop_table(data_product.table_name)

            # Remove from registry
            del registry[data_product_id]
            self._save_registry(registry)

            return {"message": "Data product deleted successfully"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete data product: {str(e)}")
