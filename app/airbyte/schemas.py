"""Pydantic models for Airbyte API payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union, List, Dict, Any

from pydantic import BaseModel, Field, SecretStr, validator, field_validator
from enum import Enum

# Pre-defined source definition mappings (extracted from Airbyte API)
SOURCE_DEFINITIONS = {
    "postgres": {
        "id": "decd338e-5647-4c0b-adf4-da0e75f5a750",
        "name": "Postgres",
        "dockerRepository": "airbyte/source-postgres",
        "dockerImageTag": "3.6.35",
    },
    "mysql": {
        "id": "435bb9a5-7887-4809-aa58-28c27df0d7ad",
        "name": "MySQL",
        "dockerRepository": "airbyte/source-mysql",
        "dockerImageTag": "3.50.5",
    },
    "mongodb": {
        "id": "b2e713cd-cc36-4c0a-b5bd-b47cb8a0561e",
        "name": "MongoDb",
        "dockerRepository": "airbyte/source-mongodb-v2",
        "dockerImageTag": "2.0.2",
    },
    "kafka": {
        "id": "d917a47b-8537-4d0d-8c10-36a9928d4265",
        "name": "Kafka",
        "dockerRepository": "airbyte/source-kafka",
        "dockerImageTag": "0.4.2",
    },
}


# Pre-defined destination definition mappings
DESTINATION_DEFINITIONS = {
    "s3": {
        "id": "4816b78f-1489-44c1-9060-4b19d5fa9362",
        "name": "S3",
        "dockerRepository": "airbyte/destination-s3",
        "dockerImageTag": "0.3.17",
    },
}


class DataSourceType(str, Enum):
    """Supported source connector types with their Airbyte definition IDs."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    KAFKA = "kafka"


class DataDestinationType(str, Enum):
    """Supported destination connector types."""

    S3 = "s3"


class PostgresConfig(BaseModel):
    host: str = Field(..., example="localhost")
    port: int = Field(5432, example=5432)
    database: str = Field(..., example="postgres")
    username: str = Field(..., example="postgres")
    password: SecretStr = Field(..., example="password")

    ssl_mode: Dict[str, Any] = Field(
        default={"mode": "require"}, example={"mode": "disable,require,verify-ca,verify-full"}
    )
    replication_method: Dict[str, Any] = Field(
        default={"method": "Standard"}, example={"method": "Standard,CDC"}
    )
    # tunnel_method: Union[str, TunnelMethod] = Field("NO_TUNNEL", example="NO_TUNNEL,SSH")
    source_type: str = Field("postgres", example="postgres")

    @validator("port")
    def port_must_be_valid(cls, v: int) -> int:
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v

    # class Config:
    #     allow_population_by_field_name = True


# class PostgresConfig(BaseModel):
#             allow_population_by_field_name = True


class MySQLConfig(BaseModel):
    """Configuration for a MySQL connector."""

    host: str = Field(..., example="localhost")
    port: int = Field(3306, example=3306)
    database: str = Field(..., example="mysql_db")
    username: str = Field(..., example="root")
    password: SecretStr = Field(..., example="password")
    # charset: str = Field("utf8mb4", example="utf8mb4")

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


class MongoDBConfig(BaseModel):
    """Configuration for a MongoDB connector."""

    connection_string: str = Field(..., example="mongodb://localhost:27017/")
    database: str = Field(..., example="mydb")
    auth_source: str = Field("admin", example="admin")


class S3Config(BaseModel):
    """Configuration for an S3 destination connector."""

    s3_bucket_name: str = Field(..., example="my-bucket")
    s3_bucket_region: str = Field(..., example="us-east-1")
    access_key_id: str = Field(..., example="AKIAIOSFODNN7EXAMPLE")
    secret_access_key: SecretStr = Field(..., example="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    s3_bucket_path: str = Field("", example="exports/")
    format: Dict[str, Any] = Field(
        default={"format_type": "Parquet", "flattening": "No flattening"},
        example={"format_type": "Parquet", "flattening": "No flattening"},
    )
    destinationType: str = Field("s3", example="s3")


class DataSourcePayload(BaseModel):
    """Payload describing a data source using typed configs."""

    name: str = Field(..., example="my_source")
    type: DataSourceType
    config: Union[
        PostgresConfig,
        MySQLConfig,
        KafkaConfig,
        MongoDBConfig,
    ]
    workspace: Optional[str] = Field(None, example="Default Workspace")


class DataSourceResponse(BaseModel):
    """Data source response returned from the API."""

    id: str = Field(..., example="12345678-1234-1234-1234-123456789012")
    name: str = Field(..., example="my_source")
    type: DataSourceType
    config: Union[
        PostgresConfig,
        MySQLConfig,
        KafkaConfig,
        MongoDBConfig,
    ]


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


class ScheduleConfig(BaseModel):
    """Schedule configuration for connections."""

    scheduleType: str = Field(
        ..., example="cron", description="Type of schedule (cron, basic, manual)"
    )
    cronExpression: Optional[str] = Field(
        None, example="0 0 12 * * ?", description="Cron expression for scheduling"
    )


class IngestionPayload(BaseModel):
    """Payload for creating a connection between an existing source and destination."""

    name: str = Field(..., example="Postgres-to-Bigquery", description="Name for the connection")
    sourceId: str = Field(
        ..., example="95e66a59-8045-4307-9678-63bc3c9b8c93", description="ID of the source"
    )
    destinationId: str = Field(
        ..., example="e478de0d-a3a0-475c-b019-25f7dd29e281", description="ID of the destination"
    )
    schedule: Optional[ScheduleConfig] = Field(None, description="Optional schedule configuration")
    status: Optional[str] = Field(
        "active", example="active", description="Connection status (active, inactive)"
    )


class IngestionResponse(BaseModel):
    """Response returned after creating an ingestion connection."""

    connectionId: str = Field(..., description="Unique identifier for the created connection")
    sourceId: str = Field(..., description="ID of the source")
    destinationId: str = Field(..., description="ID of the destination")
    name: str = Field(..., description="Name of the connection")
    status: str = Field(..., description="Status of the connection")
    schedule: Optional[ScheduleConfig] = Field(None, description="Schedule configuration if set")
    created: datetime = Field(..., description="Creation timestamp")


class IngestionStatusResponse(BaseModel):
    """Response returned when checking ingestion connection status."""

    ingestionId: str = Field(..., description="Unique identifier for the connection")
    status: str = Field(..., description="Current status of the connection")
    lastSync: Optional[datetime] = Field(None, description="Last synchronization timestamp")
    nextSync: Optional[datetime] = Field(
        None, description="Next scheduled synchronization timestamp"
    )
    schedule: Optional[ScheduleConfig] = Field(None, description="Schedule configuration if set")


class DataSourceListItem(BaseModel):
    """Individual source item in the list response."""

    sourceId: str = Field(..., description="Unique identifier for the source")
    name: str = Field(..., description="Name of the source")
    sourceName: str = Field(..., description="Type name of the source connector")
    workspaceId: str = Field(..., description="Workspace ID")


class DataSourceListResponse(BaseModel):
    """Response model for listing all sources."""

    sources: List[DataSourceListItem] = Field(..., description="List of sources")
    total: int = Field(..., description="Total number of sources")


class DataSinkListItem(BaseModel):
    """Individual destination item in the list response."""

    destinationId: str = Field(..., description="Unique identifier for the destination")
    name: str = Field(..., description="Name of the destination")
    destinationName: str = Field(..., description="Type name of the destination connector")
    workspaceId: str = Field(..., description="Workspace ID")


class DataSinkListResponse(BaseModel):
    """Response model for listing all destinations."""

    destinations: List[DataSinkListItem] = Field(..., description="List of destinations")
    total: int = Field(..., description="Total number of destinations")


def get_destination_definition_id(dest_type: DataDestinationType) -> str:
    """Get the Airbyte destination definition ID for a given destination type."""
    definition = DESTINATION_DEFINITIONS.get(dest_type.value)
    if not definition:
        raise ValueError(f"Unsupported destination type: {dest_type}")
    return definition["id"]


def get_destination_definition(dest_type: DataDestinationType) -> Dict[str, str]:
    """Get the complete destination definition for a given destination type."""
    definition = DESTINATION_DEFINITIONS.get(dest_type.value)
    if not definition:
        raise ValueError(f"Unsupported destination type: {dest_type}")
    return definition


def list_available_destinations() -> List[Dict[str, str]]:
    """List all available destination definitions."""
    return [
        {"type": dest_type, "name": definition["name"], "id": definition["id"]}
        for dest_type, definition in DESTINATION_DEFINITIONS.items()
    ]


# Helper functions
def get_source_definition_id(source_type: DataSourceType) -> str:
    """Get the Airbyte source definition ID for a given source type."""
    definition = SOURCE_DEFINITIONS.get(source_type.value)
    if not definition:
        raise ValueError(f"Unsupported source type: {source_type}")
    return definition["id"]


def get_source_definition(source_type: DataSourceType) -> Dict[str, str]:
    """Get the complete source definition for a given source type."""
    definition = SOURCE_DEFINITIONS.get(source_type.value)
    if not definition:
        raise ValueError(f"Unsupported source type: {source_type}")
    return definition


def list_available_sources() -> List[Dict[str, str]]:
    """List all available source definitions."""
    return [
        {"type": source_type, "name": definition["name"], "id": definition["id"]}
        for source_type, definition in SOURCE_DEFINITIONS.items()
    ]
