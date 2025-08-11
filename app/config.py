from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    airbyte_base_url: str = "http://localhost:8000/api/v1"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)


def get_settings() -> Settings:
    return Settings()
