# Asgard Data Platform

A comprehensive FastAPI wrapper for data operations including:

- **Airbyte Integration**: Simplified data source and sink management for data ingestion
- **Spark Transformations**: Kubernetes-based data transformations using SparkOperator

This platform provides unified REST interfaces to manage your entire data pipeline from ingestion to transformation.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Running Airbyte instance (for data ingestion features)
- Kubernetes cluster with SparkOperator (for transformations)

### 1. Setup

```bash
# Clone the repository
git clone <repository-url>
cd asgard-dev

# Set up environment variables
cp .env.example .env
# Edit .env with your service configuration

# Sync dependencies
uv sync
```

### 2. Configure Services

Update `.env` with your service details:

```bash
# Airbyte Configuration
AIRBYTE_BASE_URL=http://localhost:8000

# Kubernetes Configuration (for Spark transformations)
PIPELINE_NAMESPACE=asgard
SPARK_IMAGE=your-registry/spark-custom:latest
SPARK_SERVICE_ACCOUNT=spark-sa
S3_SECRET_NAME=s3-credentials
```

### 3. Start the API

The API will be available at:

- **API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Transformation**: http://localhost:8001/transformation

## 📖 API Usage

### Spark Transformations

#### Submit a Spark Transformation Job

**Note**: The `/transform` API automatically detects source and destination from Airbyte S3 sinks. All Spark configuration has sensible defaults.

```bash
curl -X POST "http://localhost:8001/transform" \
     -H "Content-Type: application/json" \
     -d '{
       "sql": "SELECT customer_id, SUM(amount) as total_amount FROM source_data GROUP BY customer_id"
     }'
```

**Optional**: You can still override Spark configuration if needed:

```bash
curl -X POST "http://localhost:8001/transform" \
     -H "Content-Type: application/json" \
     -d '{

       "sql": "SELECT customer_id, SUM(amount) as total_amount FROM source_data GROUP BY customer_id",
       "write_mode": "overwrite",
       "executor_instances": 4,
       "executor_memory": "8g"
     }'
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

### Spark Transformation API (Kubernetes Integration)

- `POST /transform` - Submit Spark transformation job (auto-detects source/destination)

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

| Variable                | Description                          | Default                 |
| ----------------------- | ------------------------------------ | ----------------------- |
| `AIRBYTE_BASE_URL`      | Airbyte base URL                     | `http://localhost:8000` |
| `PIPELINE_NAMESPACE`    | Kubernetes namespace for Spark jobs  | `asgard`                |
| `SPARK_IMAGE`           | Docker image for Spark jobs          | Required                |
| `SPARK_SERVICE_ACCOUNT` | Kubernetes service account           | `spark-sa`              |
| `S3_SECRET_NAME`        | Kubernetes secret for S3 credentials | `s3-credentials`        |

### Request Schema

#### Spark Transformation Request (Kubernetes)

**Minimal Request** (recommended):

```json
{
  "sql": "string"
}
```

**With Optional Spark Configuration** (all have sensible defaults):

```json
{
  "sql": "string",
  "write_mode": "overwrite|append",
  "executor_instances": 2,
  "executor_cores": 2,
  "executor_memory": "4g",
  "driver_cores": 1,
  "driver_memory": "2g"
}
```

**Note**: Both transformation APIs automatically determine source and destination from registered Airbyte S3 sinks. The system uses the first available S3 sink as the source location and creates the destination in the same bucket under the 'silver/' folder.

#### Data Source/Sink Request

```json
{
  "source_type": "postgres|mysql|mongodb|kafka",
  "destination_type": "s3",
  "workspace_name": "default",
  "config": {
    "s3_bucket_name": "string",
    "s3_bucket_path": "string"
  },
  "name": "string"
}
```

## 🏗️ Architecture

### Data Transformation Pipeline

```
Client Request → FastAPI → Kubernetes → SparkApplication → S3 Output
```

### Data Ingestion Pipeline

```
Client Request → FastAPI → Airbyte API → Data Sources → Data Sinks
```

### Unified Workflow

```
1. Data Sources → Airbyte Ingestion → S3 Bronze Layer
2. S3 Bronze Layer → Spark Transformation → S3 Silver Layer
3. S3 Silver Layer → Further Processing → S3 Gold Layer
```

The platform provides:

#### Airbyte Integration:

1. Simplified data source configuration (Postgres, MySQL, MongoDB, Kafka)
2. Data sink management (S3, etc.)
3. Connection and ingestion job management
4. Automated data pipeline setup

#### Airflow Integration:

1. **Automatic Source Detection**: Uses registered Airbyte S3 sinks as transformation sources

#### Spark Integration:

1. **Automatic Source Detection**: Uses registered Airbyte S3 sinks as transformation sources
2. **Medallion Architecture**: Automatically creates 'silver' layer destinations
3. Converts SQL queries to Kubernetes SparkApplications
4. Executes Spark jobs on Kubernetes using SparkOperator
5. Returns job status and execution details

#### Typical Workflow:

1. **Bronze Layer**: Register S3 sink via `/sink` endpoint → Ingest raw data via Airbyte
2. **Silver Layer**: Submit transformation job via `/transform` → Process data with Spark
3. **Gold Layer**: Run additional transformations for analytics-ready data

## 📁 Project Structure

```
asgard-dev/
├── app/
│   ├── airbyte/          # Airbyte integration (data ingestion)
│   ├── data_transformation/ # Spark transformation (Kubernetes)
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── .env                  # Environment variables
├── pyproject.toml        # Dependencies and config
├── uv.lock               # Lock file
```

## 🔒 Security

- Basic SQL injection protection
- Environment-based configuration
- No sensitive data in code
