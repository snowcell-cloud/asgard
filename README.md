# Asgard Data Platform

A comprehensive FastAPI wrapper for data operations including:

- **Airbyte Integration**: Simplified data source and sink management for data ingestion
- **Airflow Transformations**: Spark-based data transformations through Airflow API

This platform provides unified REST interfaces to manage your entire data pipeline from ingestion to transformation.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Running Airflow instance with API access
- Valid Airflow Bearer token
- Running Airbyte instance (optional, for data ingestion features)

### 1. Setup

```bash
# Clone the repository
git clone <repository-url>
cd asgard-dev

# Set up environment variables
cp .env.example .env
# Edit .env with your Airflow Bearer token

# Sync dependencies
uv sync
```

### 2. Configure Services

Update `.env` with your service details:

```bash
# Airflow Configuration
AIRFLOW_BASE_URL=http://localhost:8080
AIRFLOW_API_BASE_URL=http://localhost:8080/api/v2
AIRFLOW_BEARER_TOKEN=your_actual_bearer_token_here

# Airbyte Configuration
AIRBYTE_BASE_URL=http://localhost:8000
```

### 3. Start the API

The API will be available at:

- **API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Transformation**: http://localhost:8001/transformation

## 📖 API Usage

### Airflow Transformations

#### Submit a Transformation Job

```bash
curl -X POST "http://localhost:8001/transformation" \
     -H "Content-Type: application/json" \
     -d '{
       "source": {
         "bucket": "my-source-bucket",
         "path": "data/input/"
       },
       "destination": {
         "bucket": "my-dest-bucket",
         "path": "data/output/"
       },
       "sql_query": "SELECT customer_id, SUM(amount) as total FROM source_data GROUP BY customer_id",
       "job_name": "Customer Aggregation"
     }'
```

#### Check Job Status

```bash
curl "http://localhost:8001/transformation/{job_id}"
```

#### List All Jobs

```bash
curl "http://localhost:8001/transformation"
```

### Airbyte Data Integration

#### Create a Data Source

```bash
curl -X POST "http://localhost:8001/datasource" \
     -H "Content-Type: application/json" \
     -d '{
       "source_type": "postgres",
       "workspace_name": "default",
       "source_config": {
         "host": "localhost",
         "port": 5432,
         "username": "user",
         "password": "password",
         "database": "mydb"
       },
       "name": "My Postgres Source"
     }'
```

#### Create a Data Sink

```bash
curl -X POST "http://localhost:8001/sink" \
     -H "Content-Type: application/json" \
     -d '{
       "destination_type": "s3",
       "workspace_name": "default",
       "destination_config": {
         "bucket_name": "my-data-bucket",
         "aws_access_key_id": "your_key",
         "aws_secret_access_key": "your_secret"
       },
       "name": "My S3 Sink"
     }'
```

#### Start Data Ingestion

```bash
curl -X POST "http://localhost:8001/ingestion" \
     -H "Content-Type: application/json" \
     -d '{
       "source_id": "source-uuid-here",
       "destination_id": "destination-uuid-here",
       "workspace_name": "default",
       "connection_name": "Postgres to S3 Sync"
     }'
```

#### List Data Sources and Sinks

```bash
# List data sources
curl "http://localhost:8001/datasource"

# List data sinks
curl "http://localhost:8001/sink"
```

 
## 📋 API Endpoints

### Transformation API (Airflow Integration)
- `GET /health` - Health check
- `POST /transformation` - Submit transformation job
- `GET /transformation/{job_id}` - Get job status
- `GET /transformation` - List jobs
- `GET /transformation/health/status` - Service health
- `GET /transformation/dags/list` - List Airflow DAGs

### Airbyte Integration API

- `GET /datasource` - List available data sources
- `POST /datasource` - Create new data source
- `GET /sink` - List available data sinks
- `POST /sink` - Create new data sink
- `POST /ingestion` - Start data ingestion job

### Documentation

- `GET /docs` - Interactive API documentation

## 🔧 Configuration

### Environment Variables

| Variable               | Description       | Default                        |
| ---------------------- | ----------------- | ------------------------------ |
| `AIRFLOW_BASE_URL`     | Airflow base URL  | `http://localhost:8080`        |
| `AIRFLOW_API_BASE_URL` | Airflow API URL   | `http://localhost:8080/api/v2` |
| `AIRFLOW_BEARER_TOKEN` | Airflow API token | Required                       |
| `AIRBYTE_BASE_URL`     | Airbyte base URL  | `http://localhost:8000`        |

### Request Schema

```json
{
  "source": {
    "bucket": "string",
    "path": "string"
  },
  "destination": {
    "bucket": "string",
    "path": "string"
  },
  "sql_query": "string",
  "source_format": "parquet",
  "destination_format": "parquet",
  "job_name": "string",
  "description": "string",
  "spark_options": {}
}

```
## 🏗️ Architecture

### Data Transformation Pipeline

```
Client Request → FastAPI → Airflow REST API → Spark DAG → S3 Output
```

### Data Ingestion Pipeline

```
Client Request → FastAPI → Airbyte API → Data Sources → Data Sinks
```

### Unified Workflow

```
Data Sources → Airbyte Ingestion → S3 Storage → Airflow Transformation → Final Output
```

The platform provides:

#### Airbyte Integration:

1. Simplified data source configuration (Postgres, MySQL, MongoDB, Kafka)
2. Data sink management (S3, etc.)
3. Connection and ingestion job management
4. Automated data pipeline setup

#### Airflow Integration:

1. Receives transformation requests via REST API
2. Converts them to Airflow DAG configurations
3. Triggers Airflow DAGs using Bearer token authentication
4. Tracks job status through Airflow REST API
5. Returns job status and results

## 📁 Project Structure

```
asgard-dev/
├── app/
│   ├── airflow/          # Airflow integration (transformations)
│   ├── airbyte/          # Airbyte integration (data ingestion)
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── .env                  # Environment variables
├── pyproject.toml        # Dependencies and config
├── uv.lock               # Lock file
```

## 🔒 Security

- Uses Bearer token authentication for Airflow API
- Basic SQL injection protection
- Environment-based configuration
- No sensitive data in code

 