"""
Application configuration management
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(
        default="Data Lake Transformation API", description="Application name"
    )
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host address")
    port: int = Field(default=8000, description="Port number")
    workers: int = Field(default=4, description="Number of worker processes")
    log_level: str = Field(default="INFO", description="Logging level")

    # Security settings
    secret_key: str = Field(..., description="Secret key for JWT tokens")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Token expiration time"
    )
    allowed_hosts: List[str] = Field(
        default=["*"], description="Allowed hosts for CORS"
    )

    # Database settings
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = Field(
        default=10, description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20, description="Database max overflow connections"
    )

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )
    redis_db: int = Field(default=0, description="Redis database number")
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")

    # AWS settings
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_access_key_id: Optional[str] = Field(
        default=None, description="AWS access key ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret access key"
    )
    aws_session_token: Optional[str] = Field(
        default=None, description="AWS session token"
    )

    # S3 settings
    s3_bucket: str = Field(..., description="S3 bucket name for data lake")
    s3_bronze_prefix: str = Field(default="data", description="Bronze layer prefix")
    s3_silver_prefix: str = Field(default="silver", description="Silver layer prefix")
    s3_scripts_bucket: str = Field(..., description="S3 bucket for Spark scripts")

    # EMR settings
    emr_cluster_id: Optional[str] = Field(default=None, description="EMR cluster ID")
    emr_service_role: str = Field(
        default="EMR_DefaultRole", description="EMR service role"
    )
    emr_job_flow_role: str = Field(
        default="EMR_EC2_DefaultRole", description="EMR job flow role"
    )
    emr_log_uri: Optional[str] = Field(default=None, description="EMR log URI")

    # Glue settings
    glue_job_name: str = Field(
        default="data-transformation-job", description="Glue job name"
    )
    glue_service_role: str = Field(..., description="Glue service role ARN")
    glue_script_location: str = Field(..., description="S3 path to Glue script")
    glue_temp_dir: str = Field(
        default="s3://your-bucket/temp/", description="Glue temporary directory"
    )
    glue_worker_type: str = Field(default="G.1X", description="Glue worker type")
    glue_number_of_workers: int = Field(default=5, description="Number of Glue workers")

    # Spark settings
    spark_script_s3_path: str = Field(
        ..., description="S3 path to PySpark transformation script"
    )

    # Job execution settings
    max_concurrent_jobs: int = Field(default=10, description="Maximum concurrent jobs")
    job_timeout_minutes: int = Field(default=60, description="Job timeout in minutes")
    monitoring_interval_seconds: int = Field(
        default=30, description="Job monitoring interval"
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per minute"
    )
    rate_limit_burst: int = Field(default=10, description="Rate limit burst size")

    # Data validation
    max_query_length: int = Field(default=10000, description="Maximum SQL query length")
    max_column_operations: int = Field(
        default=50, description="Maximum column operations per transformation"
    )
    max_tags: int = Field(default=10, description="Maximum tags per transformation")

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of: {valid_levels}")
        return v.upper()

    @validator("allowed_hosts")
    def validate_allowed_hosts(cls, v):
        if not v:
            return ["*"]
        return v

    @validator("workers")
    def validate_workers(cls, v):
        if v < 1:
            raise ValueError("workers must be at least 1")
        return v

    @validator("port")
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v

    # Environment-specific configurations
    @property
    def database_config(self) -> dict:
        """Get database configuration"""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "echo": self.debug,
        }

    @property
    def redis_config(self) -> dict:
        """Get Redis configuration"""
        return {
            "url": self.redis_url,
            "db": self.redis_db,
            "decode_responses": True,
            "health_check_interval": 30,
        }

    @property
    def aws_config(self) -> dict:
        """Get AWS configuration"""
        config = {
            "region_name": self.aws_region,
        }

        if self.aws_access_key_id and self.aws_secret_access_key:
            config.update(
                {
                    "aws_access_key_id": self.aws_access_key_id,
                    "aws_secret_access_key": self.aws_secret_access_key,
                }
            )

        if self.aws_session_token:
            config["aws_session_token"] = self.aws_session_token

        return config

    @property
    def s3_paths(self) -> dict:
        """Get S3 path configuration"""
        return {
            "bucket": self.s3_bucket,
            "bronze_prefix": self.s3_bronze_prefix,
            "silver_prefix": self.s3_silver_prefix,
            "scripts_bucket": self.s3_scripts_bucket,
        }

    @property
    def glue_config(self) -> dict:
        """Get Glue configuration"""
        return {
            "job_name": self.glue_job_name,
            "role": self.glue_service_role,
            "script_location": self.glue_script_location,
            "temp_dir": self.glue_temp_dir,
            "worker_type": self.glue_worker_type,
            "number_of_workers": self.glue_number_of_workers,
        }

    @property
    def emr_config(self) -> dict:
        """Get EMR configuration"""
        return {
            "cluster_id": self.emr_cluster_id,
            "service_role": self.emr_service_role,
            "job_flow_role": self.emr_job_flow_role,
            "log_uri": self.emr_log_uri,
        }


class DevelopmentSettings(Settings):
    """Development environment settings"""

    debug: bool = True
    log_level: str = "DEBUG"
    allowed_hosts: List[str] = ["*"]


class ProductionSettings(Settings):
    """Production environment settings"""

    debug: bool = False
    log_level: str = "INFO"
    workers: int = 4

    @validator("secret_key")
    def validate_secret_key_length(cls, v):
        if len(v) < 32:
            raise ValueError(
                "secret_key must be at least 32 characters long in production"
            )
        return v


class TestSettings(Settings):
    """Test environment settings"""

    debug: bool = True
    log_level: str = "DEBUG"
    database_url: str = "sqlite+aiosqlite:///./test.db"
    redis_url: str = "redis://localhost:6379/1"  # Use different Redis DB for tests


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    import os

    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()
