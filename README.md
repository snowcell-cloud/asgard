# Asgard - Airbyte FastAPI Wrapper

This service exposes a simplified HTTP API that proxies selected parts of the
[Airbyte](https://airbyte.com) API. It provides three endpoints that let you
register data sources and sinks in Airbyte and automatically connect them with a
connection .

## 🚀 Deployment

This application is containerized and deployed to Kubernetes using Helm with a CI/CD pipeline.

### Local Development

```bash
# Install dependencies with uv
uv sync

# Run the application
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

 ```

### Docker

```bash
# Build image
docker build -t asgard-app .

# Run container
docker run -p 8000:8000 asgard-app

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### Kubernetes Deployment

The application is deployed using Helm charts with GitHub Actions CI/CD:

```bash
# Deploy to Kubernetes
helm upgrade --install asgard-app ./helmchart \
  --namespace asgard \
  --create-namespace

# Test with port forwarding
kubectl port-forward svc/asgard-app 8080:80 -n asgard
curl http://localhost:8080/health
```

## 📋 Available Endpoints

All endpoints are mounted at the application root:

- `GET /health` – health check endpoint
- `GET /docs` – interactive API documentation (Swagger UI)
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

## ⚙️ Configuration

The application requires access to a running Airbyte instance. Configure the
connection via environment variables:

- `AIRBYTE_BASE_URL` – Base URL of the Airbyte API (default: http://localhost:8000/api/v1)
- `AIRBYTE_WORKSPACE_ID` – Optional workspace ID. When omitted, the first workspace returned by the Airbyte API is used.
- `ENVIRONMENT` – Environment setting (default: production)

## 🔧 CI/CD Pipeline

The project uses GitHub Actions for automated deployment:

1. **Build**: Creates Docker image with multi-stage build including tests
2. **Push**: Pushes image to AWS ECR registry
3. **Deploy**: Uses Helm to deploy to Kubernetes cluster

### Required GitHub Secrets:

- `AWS_ACCESS_KEY_ID` - AWS access key for ECR
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for ECR
- `KUBECONFIG` - Kubernetes cluster configuration

## 🏗️ Project Structure

```
.
├── app/                    # Application source code
│   ├── airbyte/           # Airbyte API client and routes
│   ├── config.py          # Application configuration
│   └── main.py            # FastAPI application entry point
├── helmchart/             # Helm chart for Kubernetes deployment
│   ├── templates/         # Kubernetes manifests
│   └── values.yaml        # Helm configuration
├── .github/workflows/     # CI/CD pipeline
├── Dockerfile             # Multi-stage Docker build
├── pyproject.toml         # Project dependencies and metadata
└── uv.lock               # Dependency lock file
```

## 🚦 Health Monitoring

- Health check endpoint: `/health`
- Application logs via `kubectl logs`
- Kubernetes readiness and liveness probes
- Resource limits and requests configured
