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
        "dockerImageTag": "3.6.35"
    },
    "mysql": {
        "id": "435bb9a5-7887-4809-aa58-28c27df0d7ad", 
        "name": "MySQL",
        "dockerRepository": "airbyte/source-mysql",
        "dockerImageTag": "3.50.5"
    },
    "mongodb": {
        "id": "b2e713cd-cc36-4c0a-b5bd-b47cb8a0561e",
        "name": "MongoDb",
        "dockerRepository": "airbyte/source-mongodb-v2", 
        "dockerImageTag": "2.0.2"
    }, 
    "kafka": {
        "id": "d917a47b-8537-4d0d-8c10-36a9928d4265",
        "name": "Kafka", 
        "dockerRepository": "airbyte/source-kafka",
        "dockerImageTag": "0.4.2"
    },
}
 

# Pre-defined destination definition mappings
DESTINATION_DEFINITIONS = {
    "s3": {
        "id": "4816b78f-1489-44c1-9060-4b19d5fa9362",
        "name": "S3",
        "dockerRepository": "airbyte/destination-s3",
        "dockerImageTag": "0.3.17"
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
    """Configuration for a Postgres connector."""
    host: str = Field(..., example="localhost")
    port: int = Field(5432, example=5432)
    database: str = Field(..., example="postgres")
    username: str = Field(..., example="postgres")
    password: SecretStr = Field(..., example="password")
    # schema: str = Field("public", example="public")
    # ssl_mode: str = Field("prefer", example="prefer")

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
        default={"format_type": "JSONL", "flattening": "Root level flattening"}, 
        example={"format_type": "JSONL", "flattening": "Root level flattening"}
    )

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
        {
            "type": dest_type,
            "name": definition["name"],
            "id": definition["id"]
        }
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
        {
            "type": source_type,
            "name": definition["name"],
            "id": definition["id"]
        }
        for source_type, definition in SOURCE_DEFINITIONS.items()
    ]
