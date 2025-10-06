"""
Service layer for dbt transformations.

This service handles the creation and execution of dynamic dbt models
for transforming silver layer data to gold layer using Trino and Iceberg.
"""

import os
import json
import uuid
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from jinja2 import Template

from fastapi import HTTPException

from .schemas import (
    DBTTransformationRequest,
    DBTTransformationResponse,
    TransformationStatus,
    SilverLayerSource,
    GoldLayerTable,
    MaterializationType,
)


class DBTTransformationService:
    """Service for managing dbt transformations from silver to gold layer."""

    def __init__(self):
        """Initialize the service with configuration."""
        # Use a writable temporary directory for dbt projects in production
        default_dbt_dir = os.path.join(tempfile.gettempdir(), "dbt_projects")
        self.dbt_project_dir = os.getenv("DBT_PROJECT_DIR", default_dbt_dir)
        # Ensure the directory exists
        os.makedirs(self.dbt_project_dir, exist_ok=True)
        # Trino configuration for data-platform namespace
        self.trino_host = os.getenv("TRINO_HOST", "trino.data-platform.svc.cluster.local")
        self.trino_port = int(os.getenv("TRINO_PORT", "8080"))
        self.trino_user = os.getenv("TRINO_USER", "dbt")

        # Iceberg catalog configuration
        self.catalog = os.getenv("TRINO_CATALOG", "iceberg")
        self.silver_schema = os.getenv("SILVER_SCHEMA", "silver")
        self.gold_schema = os.getenv("GOLD_SCHEMA", "gold")

        # Nessie configuration for data-platform namespace
        self.nessie_uri = os.getenv(
            "NESSIE_URI", "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
        )
        self.nessie_ref = os.getenv("NESSIE_REF", "main")

        # AWS/S3 configuration (from secrets)
        self.s3_bucket = os.getenv("S3_BUCKET", "airbytedestination1")
        self.s3_region = os.getenv("AWS_REGION", "eu-north-1")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # Storage for transformation metadata (in production, use a database)
        self.transformations: Dict[str, Dict] = {}

    async def _ensure_schemas_exist(self):
        """Ensure required schemas exist in Trino/Iceberg."""
        try:
            from trino.dbapi import connect

            conn = connect(
                host=self.trino_host,
                port=self.trino_port,
                user=self.trino_user,
                catalog=self.catalog,
                schema="default",
                http_scheme="http",
            )

            cursor = conn.cursor()

            # Check and create gold schema if needed
            try:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.gold_schema}")
                print(f"✅ Ensured schema exists: {self.catalog}.{self.gold_schema}")
            except Exception as e:
                print(f"⚠️  Could not create gold schema: {e}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"⚠️  Could not verify schemas: {e}")
            # Don't fail the transformation, just log the warning

    async def create_dynamic_transformation(
        self, request: DBTTransformationRequest
    ) -> DBTTransformationResponse:
        """
        Create and execute a dynamic dbt transformation.

        This method:
        1. Validates the SQL query
        2. Creates a temporary dbt model file
        3. Executes the dbt run command
        4. Returns the transformation results
        """
        transformation_id = str(uuid.uuid4())

        try:
            # Create transformation metadata
            transformation_data = {
                "id": transformation_id,
                "name": request.name,
                "sql_query": request.sql_query,
                "description": request.description,
                "materialization": request.materialization,
                "tags": request.tags or [],
                "owner": request.owner,
                "incremental_strategy": request.incremental_strategy,
                "unique_key": request.unique_key,
                "status": TransformationStatus.PENDING,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            self.transformations[transformation_id] = transformation_data

            # Update status to running
            transformation_data["status"] = TransformationStatus.RUNNING
            transformation_data["updated_at"] = datetime.now(timezone.utc)

            # Ensure schemas exist
            await self._ensure_schemas_exist()

            # Create the dbt model
            model_content = self._generate_dbt_model(request)
            model_file_path = self._create_model_file(request.name, model_content)

            try:
                # Execute dbt run
                start_time = datetime.now()
                result = await self._execute_dbt_run(request.name)
                end_time = datetime.now()

                execution_time = (end_time - start_time).total_seconds()

                # Get table statistics
                table_stats = await self._get_gold_table_stats(request.name)

                # Update transformation data with results
                transformation_data.update(
                    {
                        "status": TransformationStatus.COMPLETED,
                        "updated_at": datetime.now(timezone.utc),
                        "gold_table_name": f"{self.gold_schema}.{request.name}",
                        "row_count": table_stats.get("row_count"),
                        "execution_time_seconds": execution_time,
                    }
                )

                return DBTTransformationResponse(**transformation_data)

            except Exception as e:
                # Update status to failed
                error_str = str(e)
                transformation_data.update(
                    {
                        "status": TransformationStatus.FAILED,
                        "updated_at": datetime.now(timezone.utc),
                        "error_message": error_str,
                    }
                )

                # Enhance error message for common issues
                if "Schema" in error_str and "does not exist" in error_str:
                    error_str += "\n\nℹ️  The schema referenced in your SQL query doesn't exist in the Iceberg catalog."
                    error_str += f"\n   Please ensure the schema exists or use fully qualified table names like: {self.catalog}.schema_name.table_name"

                raise HTTPException(
                    status_code=500, detail=f"Transformation execution failed: {error_str}"
                )

            finally:
                # Clean up temporary model file
                if model_file_path and os.path.exists(model_file_path):
                    os.remove(model_file_path)

        except Exception as e:
            # Update status to failed if not already done
            if transformation_id in self.transformations:
                self.transformations[transformation_id].update(
                    {
                        "status": TransformationStatus.FAILED,
                        "updated_at": datetime.now(timezone.utc),
                        "error_message": str(e),
                    }
                )

            raise HTTPException(status_code=500, detail=f"Transformation creation failed: {str(e)}")

    def _generate_dbt_model(self, request: DBTTransformationRequest) -> str:
        """Generate dbt model content from the transformation request."""

        # Build model configuration
        config = {
            "materialized": request.materialization.value,
            "schema": self.gold_schema,
        }

        if request.materialization == MaterializationType.INCREMENTAL:
            if request.incremental_strategy:
                config["incremental_strategy"] = request.incremental_strategy
            if request.unique_key:
                config["unique_key"] = request.unique_key

        if request.tags:
            config["tags"] = request.tags

        # Generate model template
        template = Template(
            """
{#- Generated dbt model for transformation: {{ name }} -#}
{#- Description: {{ description or 'No description provided' }} -#}
{#- Owner: {{ owner or 'Unknown' }} -#}
{#- Created: {{ created_at }} -#}

{{ "{{" }} config(
    {% for key, value in config.items() %}
    {{ key }}={{ value | tojson }}{{ "," if not loop.last }}
    {% endfor %}
) {{ "}}" }}

{#- Main transformation query -#}
{{ sql_query }}
        """.strip()
        )

        return template.render(
            name=request.name,
            description=request.description,
            owner=request.owner,
            created_at=datetime.now(timezone.utc).isoformat(),
            config=config,
            sql_query=request.sql_query,
        )

    def _ensure_dbt_project_structure(self):
        """Ensure the dbt project structure exists with required files."""
        project_dir = Path(self.dbt_project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create dbt_project.yml
        dbt_project_yml = project_dir / "dbt_project.yml"
        if not dbt_project_yml.exists():
            dbt_project_content = f"""
name: 'asgard_transformations'
version: '1.0.0'
config-version: 2

profile: 'asgard'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  asgard_transformations:
    gold:
      +materialized: table
      +schema: gold
"""
            with open(dbt_project_yml, "w") as f:
                f.write(dbt_project_content.strip())

        # Create profiles.yml
        profiles_yml = project_dir / "profiles.yml"
        if not profiles_yml.exists():
            profiles_content = f"""
asgard:
  target: prod
  outputs:
    prod:
      type: trino
      method: none
      user: {self.trino_user}
      host: {self.trino_host}
      port: {self.trino_port}
      catalog: {self.catalog}
      schema: {self.gold_schema}
      threads: 4
      http_scheme: http
      retries: 5
      timezone: UTC
"""
            with open(profiles_yml, "w") as f:
                f.write(profiles_content.strip())

    def _create_model_file(self, model_name: str, model_content: str) -> str:
        """Create a temporary dbt model file."""
        # Ensure dbt project structure exists
        self._ensure_dbt_project_structure()

        models_dir = Path(self.dbt_project_dir) / "models" / "gold"
        models_dir.mkdir(parents=True, exist_ok=True)

        model_file_path = models_dir / f"{model_name}.sql"

        with open(model_file_path, "w") as f:
            f.write(model_content)

        return str(model_file_path)

    async def _execute_dbt_run(self, model_name: str) -> Dict[str, Any]:
        """Execute dbt run for the specific model."""
        try:
            # Change to dbt project directory
            original_cwd = os.getcwd()
            os.chdir(self.dbt_project_dir)

            # Run dbt debug first to check connection
            debug_cmd = ["uv", "run", "dbt", "debug", "--profiles-dir", ".", "--project-dir", "."]
            debug_result = subprocess.run(debug_cmd, capture_output=True, text=True, timeout=60)

            print(f"DBT Debug Output:\n{debug_result.stdout}\n{debug_result.stderr}")

            # Run dbt command
            cmd = [
                "uv",
                "run",
                "dbt",
                "run",
                "--select",
                model_name,
                "--profiles-dir",
                ".",
                "--project-dir",
                ".",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            print(f"DBT Run Output:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

            if result.returncode != 0:
                # Include full error message
                error_msg = f"dbt run failed (return code {result.returncode}):\n"
                error_msg += f"STDOUT:\n{result.stdout}\n"
                error_msg += f"STDERR:\n{result.stderr}"
                raise Exception(error_msg)

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        finally:
            os.chdir(original_cwd)

    async def _get_gold_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for the gold layer table."""
        try:
            # This would typically use a Trino client to get actual stats
            # For now, return mock data
            return {
                "row_count": 1000,  # Would be actual count
                "size_bytes": 1024 * 1024,  # Would be actual size
            }
        except Exception:
            return {"row_count": None, "size_bytes": None}

    async def get_transformation(self, transformation_id: str) -> DBTTransformationResponse:
        """Get a specific transformation by ID."""
        if transformation_id not in self.transformations:
            raise HTTPException(
                status_code=404, detail=f"Transformation {transformation_id} not found"
            )

        transformation_data = self.transformations[transformation_id]
        return DBTTransformationResponse(**transformation_data)

    async def list_transformations(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List all transformations with pagination."""
        transformations = list(self.transformations.values())
        total_count = len(transformations)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_transformations = transformations[start_idx:end_idx]

        return {
            "transformations": [DBTTransformationResponse(**t) for t in page_transformations],
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        }

    async def delete_transformation(self, transformation_id: str) -> Dict[str, str]:
        """Delete a transformation."""
        if transformation_id not in self.transformations:
            raise HTTPException(
                status_code=404, detail=f"Transformation {transformation_id} not found"
            )

        transformation_data = self.transformations[transformation_id]
        table_name = transformation_data.get("name")

        # Remove from storage
        del self.transformations[transformation_id]

        # Optionally drop the gold table (be careful in production!)
        # await self._drop_gold_table(table_name)

        return {"message": f"Transformation {transformation_id} deleted successfully"}

    async def get_silver_layer_sources(self) -> List[SilverLayerSource]:
        """Discover available silver layer data sources."""
        try:
            # This would typically query the Trino catalog
            # For now, return mock data of common silver layer tables
            mock_sources = [
                {
                    "table_name": "customer_data",
                    "schema_name": self.silver_schema,
                    "catalog_name": self.catalog,
                    "row_count": 50000,
                    "size_bytes": 10 * 1024 * 1024,
                    "last_modified": datetime.now(timezone.utc),
                    "columns": [
                        {"name": "customer_id", "type": "bigint"},
                        {"name": "name", "type": "varchar"},
                        {"name": "email", "type": "varchar"},
                        {"name": "created_at", "type": "timestamp"},
                    ],
                    "location": "s3://your-bucket/silver/customer_data/",
                },
                {
                    "table_name": "transaction_data",
                    "schema_name": self.silver_schema,
                    "catalog_name": self.catalog,
                    "row_count": 1000000,
                    "size_bytes": 100 * 1024 * 1024,
                    "last_modified": datetime.now(timezone.utc),
                    "columns": [
                        {"name": "transaction_id", "type": "bigint"},
                        {"name": "customer_id", "type": "bigint"},
                        {"name": "amount", "type": "decimal(10,2)"},
                        {"name": "transaction_date", "type": "date"},
                    ],
                    "location": "s3://your-bucket/silver/transaction_data/",
                },
                {
                    "table_name": "product_data",
                    "schema_name": self.silver_schema,
                    "catalog_name": self.catalog,
                    "row_count": 10000,
                    "size_bytes": 5 * 1024 * 1024,
                    "last_modified": datetime.now(timezone.utc),
                    "columns": [
                        {"name": "product_id", "type": "bigint"},
                        {"name": "product_name", "type": "varchar"},
                        {"name": "category", "type": "varchar"},
                        {"name": "price", "type": "decimal(8,2)"},
                    ],
                    "location": "s3://your-bucket/silver/product_data/",
                },
            ]

            return [SilverLayerSource(**source) for source in mock_sources]

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve silver layer sources: {str(e)}"
            )

    async def get_gold_layer_tables(self) -> List[GoldLayerTable]:
        """List all gold layer tables created by transformations."""
        try:
            tables = []

            for transformation_data in self.transformations.values():
                if transformation_data.get("status") == TransformationStatus.COMPLETED:
                    table_data = {
                        "table_name": transformation_data["name"],
                        "transformation_name": transformation_data["name"],
                        "row_count": transformation_data.get("row_count", 0),
                        "size_bytes": 1024 * 1024,  # Mock size
                        "created_at": transformation_data["created_at"],
                        "last_updated": transformation_data["updated_at"],
                        "location": f"s3://your-bucket/gold/{transformation_data['name']}/",
                        "materialization": MaterializationType(
                            transformation_data["materialization"]
                        ),
                        "tags": transformation_data.get("tags", []),
                    }
                    tables.append(GoldLayerTable(**table_data))

            return tables

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve gold layer tables: {str(e)}"
            )

    async def validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate SQL query and suggest silver layer tables."""
        try:
            # Basic validation is done by the Pydantic model
            # Here we can add more sophisticated analysis

            # Extract potential table references
            import re

            table_pattern = r"\b(silver\.\w+|\w+)\b"
            potential_tables = re.findall(table_pattern, sql_query.lower())

            # Get available silver tables
            silver_sources = await self.get_silver_layer_sources()
            available_tables = [f"silver.{source.table_name}" for source in silver_sources]

            # Find matching tables
            suggested_tables = []
            for table in potential_tables:
                if table in available_tables or f"silver.{table}" in available_tables:
                    suggested_tables.append(
                        table if table.startswith("silver.") else f"silver.{table}"
                    )

            return {
                "is_valid": True,
                "message": "SQL query passed basic validation",
                "suggested_tables": list(set(suggested_tables)) if suggested_tables else None,
            }

        except Exception as e:
            return {
                "is_valid": False,
                "message": f"SQL validation failed: {str(e)}",
                "suggested_tables": None,
            }
