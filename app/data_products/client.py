"""
Client for interacting with Trino/Nessie for data product operations.
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import uuid
from urllib.parse import quote

from fastapi import HTTPException


class TrinoClient:
    """Client for executing queries against Trino/Nessie catalog."""

    def __init__(
        self,
        host: str = "trino.data-platform.svc.cluster.local",
        port: int = 8080,
        catalog: str = "iceberg",
        schema: str = "gold",
        user: str = "dbt",
    ):
        self.base_url = f"http://{host}:{port}"
        self.catalog = catalog
        self.schema = schema
        self.user = user
        self.headers = {
            "X-Trino-User": user,
            "X-Trino-Catalog": catalog,
            "X-Trino-Schema": schema,
            "Content-Type": "application/json",
        }

    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a query against Trino and return results."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Submit query
                response = await client.post(
                    f"{self.base_url}/v1/statement", headers=self.headers, data=query
                )
                response.raise_for_status()

                result = response.json()
                query_id = result.get("id")

                # Poll for results
                while True:
                    if "nextUri" in result:
                        response = await client.get(result["nextUri"], headers=self.headers)
                        response.raise_for_status()
                        result = response.json()
                    else:
                        break

                    if result.get("stats", {}).get("state") in ["FAILED", "CANCELED"]:
                        error_info = result.get("error", {})
                        raise HTTPException(
                            status_code=500,
                            detail=f"Query failed: {error_info.get('message', 'Unknown error')}",
                        )

                    if result.get("stats", {}).get("state") == "FINISHED":
                        break

                    await asyncio.sleep(0.1)

                return {
                    "query_id": query_id,
                    "columns": result.get("columns", []),
                    "data": result.get("data", []),
                    "stats": result.get("stats", {}),
                    "warnings": result.get("warnings", []),
                }

            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"Trino query failed: {str(e)}")

    async def create_table_as(
        self, table_name: str, query: str, properties: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a table using CREATE TABLE AS SELECT."""
        props_str = ""
        if properties:
            props_list = [f"'{k}' = '{v}'" for k, v in properties.items()]
            props_str = f" WITH ({', '.join(props_list)})"

        create_query = f"""
        CREATE TABLE {self.catalog}.{self.schema}.{table_name}{props_str} AS
        {query}
        """

        return await self.execute_query(create_query)

    async def drop_table(self, table_name: str) -> Dict[str, Any]:
        """Drop a table if it exists."""
        drop_query = f"DROP TABLE IF EXISTS {self.catalog}.{self.schema}.{table_name}"
        return await self.execute_query(drop_query)

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            query = f"""
            SELECT 1 FROM information_schema.tables 
            WHERE table_catalog = '{self.catalog}' 
            AND table_schema = '{self.schema}' 
            AND table_name = '{table_name}'
            """
            result = await self.execute_query(query)
            return len(result.get("data", [])) > 0
        except:
            return False

    async def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """Get table schema information."""
        query = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_catalog = '{self.catalog}'
        AND table_schema = '{self.schema}'
        AND table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        result = await self.execute_query(query)
        return [
            {"column_name": row[0], "data_type": row[1], "is_nullable": row[2]}
            for row in result.get("data", [])
        ]

    async def query_table(
        self, table_name: str, limit: int = 100, offset: int = 0, where_clause: str = ""
    ) -> Dict[str, Any]:
        """Query a data product table."""
        where_str = f" WHERE {where_clause}" if where_clause else ""
        query = f"""
        SELECT * FROM {self.catalog}.{self.schema}.{table_name}
        {where_str}
        ORDER BY data_product_updated_at DESC
        LIMIT {limit} OFFSET {offset}
        """
        return await self.execute_query(query)


class DBTClient:
    """Client for running dbt commands."""

    def __init__(self, dbt_project_dir: str = "/home/hac/downloads/code/asgard-dev/dbt"):
        self.dbt_project_dir = dbt_project_dir

    async def run_model(self, model_name: str) -> Dict[str, Any]:
        """Run a specific dbt model."""
        import subprocess
        import os

        try:
            cmd = ["dbt", "run", "--select", model_name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.dbt_project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "DBT_PROFILES_DIR": self.dbt_project_dir},
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "return_code": process.returncode,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "return_code": -1}

    async def test_model(self, model_name: str) -> Dict[str, Any]:
        """Run dbt tests for a specific model."""
        import subprocess
        import os

        try:
            cmd = ["dbt", "test", "--select", model_name]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.dbt_project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "DBT_PROFILES_DIR": self.dbt_project_dir},
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "return_code": process.returncode,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "return_code": -1}
