from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    airbyte_base_url: str = "http://localhost:8001/api/public/v1"
    # airbyte_base_url: str = "http://airbyte-airbyte-server-svc.airbyte.svc.cluster.local:8001/api/v1"

    airbyte_workspace_id: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)

def get_settings() -> Settings:
    return Settings()
 