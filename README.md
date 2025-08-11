# Airbyte FastAPI Wrapper

This project provides a minimal FastAPI application that proxies a subset of the
[Airbyte](https://airbyte.com) HTTP API. It can be used to create sources and
destinations, wire them together with a connection, and optionally trigger sync
jobs.

## Available Endpoints

- `GET /api/workspaces` – list available Airbyte workspaces
- `POST /api/sources` – create a new source
- `POST /api/destinations` – create a new destination
- `POST /api/connections` – create a connection between an existing source and
  destination
- `POST /api/connections/{connection_id}/sync` – trigger a sync for a connection
- `GET /api/jobs/{job_id}` – retrieve status for a sync job
- `POST /api/workflows` – create a source, destination and connection in one
  request. Optionally trigger an initial sync.

## Creating a Workflow

To create a full data transfer workflow, send a request to
`POST /api/workflows` with the following JSON payload:

```json
{
  "source": {
    "workspaceId": "<workspace UUID>",
    "sourceDefinitionId": "<source definition UUID>",
    "name": "my source",
    "connectionConfiguration": {}
  },
  "destination": {
    "workspaceId": "<workspace UUID>",
    "destinationDefinitionId": "<destination definition UUID>",
    "name": "my destination",
    "connectionConfiguration": {}
  },
  "connection": {
    "name": "source to destination",
    "syncCatalog": {}
  },
  "trigger_sync": true
}
```

The response contains the identifiers for the newly created source,
destination, connection and, if `trigger_sync` was `true`, the job identifier
for the initiated sync.
