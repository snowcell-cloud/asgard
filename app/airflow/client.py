"""Airflow client for triggering DAGs and managing workflows."""

import json
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException

from app.config import get_settings


class AirflowClient:
    """Client for interacting with Airflow REST API using Bearer token authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.airflow_api_base_url
        self.headers = self._get_headers()
    
    def _get_headers(self) -> Dict[str, str]:
        """Create headers with Bearer token authentication."""
        headers = {"Content-Type": "application/json"}
        
        if self.settings.airflow_bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.airflow_bearer_token}"
        else:
            raise ValueError("AIRFLOW_BEARER_TOKEN environment variable is required")
            
        return headers
    
    async def trigger_dag(
        self, 
        dag_id: str, 
        conf: Dict[str, Any],
        dag_run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a DAG run with configuration."""
        if not dag_run_id:
            dag_run_id = f"api_trigger_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
        
        url = f"{self.base_url}/dags/{dag_id}/dagRuns"
        
        payload = {
            "dag_run_id": dag_run_id,
            "conf": conf
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to trigger DAG: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Airflow connection error: {str(e)}"
                )
    
    async def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Get the status of a specific DAG run."""
        url = f"{self.base_url}/dags/{dag_id}/dagRuns/{dag_run_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to get DAG run status: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Airflow connection error: {str(e)}"
                )
    
    async def list_dags(self) -> Dict[str, Any]:
        """List all available DAGs."""
        url = f"{self.base_url}/dags"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to list DAGs: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Airflow connection error: {str(e)}"
                )

    async def get_dag_runs(self, dag_id: str, limit: int = 100) -> Dict[str, Any]:
        """Get DAG runs for a specific DAG."""
        url = f"{self.base_url}/dags/{dag_id}/dagRuns"
        params = {"limit": limit, "order_by": "-execution_date"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to get DAG runs: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Airflow connection error: {str(e)}"
                )


def get_airflow_client() -> AirflowClient:
    """Get Airflow client instance."""
    return AirflowClient()
