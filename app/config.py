import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    
    # Environment-aware configuration
    environment: str = "development"  # development, production, or staging
    
    # Airbyte configuration
    airbyte_base_url: str = None
    airbyte_workspace_id: Optional[str] = None
    
    # Airflow configuration
    airflow_base_url: str = "http://localhost:8080"
    airflow_api_base_url: str = "http://localhost:8080/api/v2"
    airflow_bearer_token: Optional[str] = None
    
    # AWS/S3 configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Spark configuration
    spark_app_name: str = "asgard-data-transform"
    spark_master: str = "local[*]"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)
    
    def __post_init__(self):
        """Set airbyte_base_url based on environment if not explicitly set."""
        if not self.airbyte_base_url:
            if self.environment.lower() in ["production", "staging"]:
                # Use Kubernetes service URL for cluster deployment
                self.airbyte_base_url = "http://airbyte-airbyte-server-svc.airbyte.svc.cluster.local:8001/api/public/v1"
            else:
                # Use localhost for development (port-forwarding)
                self.airbyte_base_url = "http://localhost:8001/api/public/v1"
    
    def model_post_init(self, __context):
        """Called after model validation."""
        if not self.airbyte_base_url:
            if self.environment.lower() in ["production", "staging"]:
                # Use Kubernetes service URL for cluster deployment
                self.airbyte_base_url = "http://airbyte-airbyte-server-svc.airbyte.svc.cluster.local:8001/api/public/v1"
            else:
                # Use localhost for development (port-forwarding)
                self.airbyte_base_url = "http://localhost:8001/api/public/v1"

def get_settings() -> Settings:
    return Settings()
 