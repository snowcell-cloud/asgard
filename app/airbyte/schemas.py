"""Pydantic models for Airbyte API payloads."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Union, List

from pydantic import BaseModel, Field, SecretStr, validator, field_validator
from enum import Enum

class DataSourceType(str, Enum):
    """Supported source connector types."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    KAFKA = "kafka"

class DataDestinationType(str, Enum):
    """Supported destination connector types."""

    S3 = "s3"

class PostgresConfig(BaseModel):
    """Configuration for a Postgres connector."""

    host: str = Field(..., example="localhost")
    port: int = Field(5432, example=5432)
    database: str = Field(..., example="postgres")
    username: str = Field(..., example="postgres")
    password: SecretStr = Field(..., example="password")
    schema: str = Field("public", example="public")
    ssl_mode: str = Field("prefer", example="prefer")

    @validator("port")
    def port_must_be_valid(cls, v: int) -> int:
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v

class MySQLConfig(BaseModel):
    """Configuration for a MySQL connector."""

    host: str = Field(..., example="localhost")
    port: int = Field(3306, example=3306)
    database: str = Field(..., example="mysql_db")
    username: str = Field(..., example="root")
    password: SecretStr = Field(..., example="password")
    charset: str = Field("utf8mb4", example="utf8mb4")

    @validator("port")
    def port_must_be_valid(cls, v: int) -> int:
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v

class KafkaConfig(BaseModel):
    """Configuration for a Kafka connector."""

    bootstrap_servers: List[str] = Field(..., example=["localhost:9092"])
    security_protocol: str = Field("PLAINTEXT", example="PLAINTEXT")
    topic: str = Field(..., example="my_topic")
    group_id: Optional[str] = Field("default_group", example="my_group")

class S3Config(BaseModel):
    """Configuration for an S3 destination connector."""

    bucket_name: str = Field(..., example="my-bucket")
    bucket_region: str = Field(..., example="us-east-1")
    access_key_id: str = Field(..., example="AKIAIOSFODNN7EXAMPLE")
    secret_access_key: SecretStr = Field(..., example="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    path_prefix: str = Field("", example="exports/")

class DataSourcePayload(BaseModel):
    """Payload describing a data source using typed configs."""

    name: str = Field(..., example="my_source")
    type: DataSourceType
    config: Union[PostgresConfig, MySQLConfig, KafkaConfig]

class DataSourceResponse(DataSourcePayload):
    """Data source payload returned from the API."""

    id: str

class DataSinkPayload(BaseModel):
    """Payload describing a data sink. Only S3 sinks are supported."""

    name: str = Field(..., example="my_sink")
    type: DataDestinationType = Field(default=DataDestinationType.S3, example="s3")
    config: S3Config

    @field_validator("type")
    @classmethod
    def ensure_s3(cls, v: DataDestinationType) -> DataDestinationType:
        if v != DataDestinationType.S3:
            raise ValueError("Only 's3' sinks are supported")
        return v

class DataSinkResponse(DataSinkPayload):
    """Data sink payload returned from the API."""

    id: str

class IngestionPayload(BaseModel):
    """Payload for linking an existing source to a sink."""

    source_id: str = Field(..., alias="sourceId")
    sink_id: str = Field(..., alias="sinkId")
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

class IngestionResponse(BaseModel):
    """Response returned after creating an ingestion."""

    id: str
    source_id: str = Field(alias="sourceId")
    sink_id: str = Field(alias="sinkId")
    created: datetime
    updated: datetime

    class Config:
        populate_by_name = True
