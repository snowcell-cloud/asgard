# Airbyte FastAPI Wrapper

This service exposes a very small HTTP API that proxies selected parts of the
[Airbyte](https://airbyte.com) API.  It provides three endpoints that let you
register data sources and sinks in Airbyte and automatically connect them with a
connection.

## Available Endpoints

All endpoints are mounted at the application root:

- `POST /datasource` – create a new Airbyte source
- `POST /sink` – create a new Airbyte destination
- `POST /ingestion` – link an existing source and sink with a connection

The backend looks up the Airbyte workspace and connector definition IDs at
request time, so the client only supplies connector configuration when creating
sources and sinks. Identifiers for the created resources are generated
automatically and returned in the response. The `/ingestion` endpoint then uses
the returned IDs to establish a connection.

## Example Payloads

Register a MySQL source:

```json
{
  "name": "mysql_source",
  "type": "mysql",
  "config": {
    "host": "localhost",
    "port": 3306,
    "database": "mysql_db",
    "username": "root",
    "password": "password"
  }
}
```
Register an S3 sink:

```json
{
  "name": "s3_sink",
  "type": "s3",
  "config": {
    "bucket_name": "my-bucket",
    "bucket_region": "us-east-1",
    "access_key_id": "AKIA...",
    "secret_access_key": "secret",
    "path_prefix": "exports/"
  }
}
```
Create an ingestion that wires them together. Optional created and updated
timestamps may be supplied by the client; otherwise the backend sets them to
the current time:

```json
{
  "sourceId": "<uuid returned from /datasource>",
  "sinkId": "<uuid returned from /sink>",
  "created": "2024-01-01T00:00:00Z",
  "updated": "2024-01-01T00:00:00Z"
}
```
The response includes the new connection ID along with the source and sink IDs
and timestamps for when the ingestion was created.
Configuration

The application requires access to a running Airbyte instance. Configure the
connection via environment variables:

    AIRBYTE_BASE_URL – Base URL of the Airbyte API (default:
    http://localhost:8000/api/v1)

    AIRBYTE_WORKSPACE_ID – Optional workspace ID. When omitted, the first
    workspace returned by the Airbyte API is used.
 