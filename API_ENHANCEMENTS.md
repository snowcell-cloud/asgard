# Airbyte Ingestion API Enhancements

## Summary

The Airbyte ingestion API has been enhanced with optional schedule and status parameters, and a new status endpoint has been added for monitoring connection status.

## Changes Made

### 1. Schema Updates (`app/airbyte/schemas.py`)

#### New `ScheduleConfig` Model

```python
class ScheduleConfig(BaseModel):
    """Schedule configuration for connections."""

    scheduleType: str = Field(..., example="cron", description="Type of schedule (cron, basic, manual)")
    cronExpression: Optional[str] = Field(None, example="0 0 * * *", description="Cron expression for scheduling")
```

#### Enhanced `IngestionPayload` Model

```python
class IngestionPayload(BaseModel):
    """Payload for creating a connection between an existing source and destination."""

    name: str = Field(..., example="Postgres-to-Bigquery", description="Name for the connection")
    sourceId: str = Field(..., example="95e66a59-8045-4307-9678-63bc3c9b8c93", description="ID of the source")
    destinationId: str = Field(..., example="e478de0d-a3a0-475c-b019-25f7dd29e281", description="ID of the destination")
    schedule: Optional[ScheduleConfig] = Field(None, description="Optional schedule configuration")
    status: Optional[str] = Field("active", example="active", description="Connection status (active, inactive)")
```

#### Updated `IngestionResponse` Model

- Added `schedule` field to include schedule configuration in responses

#### New `IngestionStatusResponse` Model

```python
class IngestionStatusResponse(BaseModel):
    """Response returned when checking ingestion connection status."""

    connectionId: str = Field(..., description="Unique identifier for the connection")
    status: str = Field(..., description="Current status of the connection")
    lastSync: Optional[datetime] = Field(None, description="Last synchronization timestamp")
    nextSync: Optional[datetime] = Field(None, description="Next scheduled synchronization timestamp")
    schedule: Optional[ScheduleConfig] = Field(None, description="Schedule configuration if set")
```

### 2. Client Updates (`app/airbyte/client.py`)

#### New `get_connection` Method

```python
async def get_connection(self, connection_id: str) -> dict:
    """Get details of a specific connection."""
    logger.info(f"Getting connection details for: {connection_id}")
    try:
        result = await self._get(f"/connections/{connection_id}")
        logger.info(f"Connection details retrieved: {connection_id}")
        return result
    except Exception as e:
        logger.error(f"Error getting connection: {e}")
        raise
```

### 3. Router Updates (`app/airbyte/router.py`)

#### Enhanced `/ingestion` POST Endpoint

- Added support for optional `schedule` and `status` parameters
- Maintains backward compatibility with existing API calls
- Properly handles schedule configuration in Airbyte connection requests

#### New `/ingestion/{connectionId}/status` GET Endpoint

```python
@router.get("/ingestion/{connectionId}/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    connectionId: str,
    client: Annotated[AirbyteClient, Depends(get_airbyte_client_dependency)]
) -> IngestionStatusResponse:
    """Get the status of an ingestion connection."""
```

## API Usage Examples

### Creating Ingestion with Full Parameters

```json
POST /ingestion
{
    "name": "postgres-to-s3-daily",
    "sourceId": "12345678-1234-1234-1234-123456789012",
    "destinationId": "87654321-4321-4321-4321-210987654321",
    "schedule": {
        "scheduleType": "cron",
        "cronExpression": "0 2 * * *"
    },
    "status": "active"
}
```

### Creating Ingestion with Minimal Parameters

```json
POST /ingestion
{
    "name": "simple-connection",
    "sourceId": "source-id",
    "destinationId": "dest-id"
}
```

### Checking Connection Status

```
GET /ingestion/{connectionId}/status
```

Response:

```json
{
  "connectionId": "conn-12345678-1234-1234-1234-123456789012",
  "status": "active",
  "lastSync": "2024-01-15T10:30:00Z",
  "nextSync": "2024-01-16T02:00:00Z",
  "schedule": {
    "scheduleType": "cron",
    "cronExpression": "0 2 * * *"
  }
}
```

## Parameter Details

### Required Parameters

- `name`: Connection name
- `sourceId`: ID of the source connector
- `destinationId`: ID of the destination connector

### Optional Parameters

- `schedule`: Schedule configuration object
  - `scheduleType`: Type of schedule ("cron", "manual", "basic")
  - `cronExpression`: Cron expression (required for "cron" scheduleType)
- `status`: Connection status ("active", "inactive") - defaults to "active"

## Schedule Types

- **cron**: Custom scheduling using cron expressions
- **manual**: Manual trigger only
- **basic**: Simple interval-based scheduling

## Backward Compatibility

All changes are fully backward compatible. Existing API calls will continue to work without modification:

- Optional parameters default to sensible values
- Existing response structures are preserved
- New fields are added without breaking existing integrations

## Testing

Comprehensive tests have been created to validate:

- ✅ Schema validation for all parameter combinations
- ✅ Backward compatibility with minimal parameters
- ✅ Optional parameter handling
- ✅ Status response structure
- ✅ Import and integration verification

## Files Modified

1. `app/airbyte/schemas.py` - Added new schemas and enhanced existing ones
2. `app/airbyte/client.py` - Added connection status retrieval method
3. `app/airbyte/router.py` - Enhanced ingestion endpoint and added status endpoint

## Files Added

1. `test_comprehensive.py` - Comprehensive test suite for new features
2. `example_usage.py` - Usage examples and documentation
3. `test_new_api.py` - Basic validation tests
