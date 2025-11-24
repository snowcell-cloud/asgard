# Asgard Platform - API Testing Guide

**Complete API Reference with Testing Examples**  
**Last Updated:** November 11, 2025  
**Version:** 1.0

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Airbyte APIs](#airbyte-apis)
3. [Spark Transformation APIs](#spark-transformation-apis)
4. [DBT Transformation APIs](#dbt-transformation-apis)
5. [Feast Feature Store APIs](#feast-feature-store-apis)
6. [MLOps APIs](#mlops-apis)
7. [Data Products APIs](#data-products-apis)
8. [Testing Tools](#testing-tools)
9. [Complete Testing Workflow](#complete-testing-workflow)

---

## Getting Started

### Prerequisites

- Asgard platform running on Kubernetes
- Port forwarding configured: `kubectl port-forward -n asgard svc/asgard-app 8000:80`
- `curl` and `jq` installed for command-line testing
- Optional: Postman or similar API client

### Base URL

```bash
export ASGARD_API=http://localhost:8000
```

### Access Swagger UI

Interactive API documentation is available at:

```bash
open http://localhost:8000/docs
```

### Health Check

```bash
curl $ASGARD_API/health | jq
```

**Expected Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "airbyte": "connected",
    "spark": "ready",
    "dbt": "ready",
    "feast": "connected",
    "mlflow": "connected"
  },
  "timestamp": "2025-11-11T10:00:00Z"
}
```

---

## Airbyte APIs

### Overview

Airbyte APIs manage data ingestion from various sources to the Bronze layer.

### List Data Sources

**Endpoint:** `GET /datasource`

```bash
curl -X GET "$ASGARD_API/datasource" | jq
```

**Response:**

```json
{
  "sources": [
    {
      "sourceId": "abc-123",
      "name": "customer_database",
      "sourceType": "postgres",
      "status": "active"
    }
  ]
}
```

### Create PostgreSQL Data Source

**Endpoint:** `POST /datasource`

```bash
curl -X POST "$ASGARD_API/datasource" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "postgres",
    "workspace_name": "default",
    "name": "customer_database",
    "source_config": {
      "host": "postgres.example.com",
      "port": 5432,
      "database": "customers",
      "username": "readonly_user",
      "password": "secure_password",
      "schemas": ["public"]
    }
  }' | jq
```

**Response:**

```json
{
  "sourceId": "abc-123-def-456",
  "name": "customer_database",
  "sourceType": "postgres",
  "status": "active",
  "streams_available": ["customers", "orders", "addresses"]
}
```

### Create MySQL Data Source

```bash
curl -X POST "$ASGARD_API/datasource" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mysql",
    "workspace_name": "default",
    "name": "transaction_system",
    "source_config": {
      "host": "mysql.example.com",
      "port": 3306,
      "database": "transactions",
      "username": "etl_user",
      "password": "secure_password"
    }
  }' | jq
```

### Create S3/Iceberg Destination

**Endpoint:** `POST /datasink`

```bash
curl -X POST "$ASGARD_API/datasink" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_type": "s3",
    "workspace_name": "default",
    "name": "bronze_iceberg_store",
    "destination_config": {
      "s3_bucket": "airbytedestination1",
      "s3_path": "iceberg/bronze",
      "region": "us-east-1",
      "format": "parquet",
      "compression": "snappy"
    }
  }' | jq
```

### Start Data Ingestion

**Endpoint:** `POST /ingestion`

```bash
curl -X POST "$ASGARD_API/ingestion" \
  -H "Content-Type: application/json" \
  -d '{
    "sourceId": "abc-123-def-456",
    "destinationId": "dest-789",
    "streams": ["customers", "transactions"],
    "schedule": {
      "scheduleType": "cron",
      "cronExpression": "0 */6 * * *"
    }
  }' | jq
```

**Response:**

```json
{
  "connectionId": "conn-xyz-789",
  "jobId": "job-101112",
  "status": "running",
  "records_synced": 0,
  "estimated_completion": "2025-11-11T10:30:00Z"
}
```

### Check Ingestion Status

**Endpoint:** `GET /ingestion/{job_id}/status`

```bash
curl -X GET "$ASGARD_API/ingestion/job-101112/status" | jq
```

**Response:**

```json
{
  "jobId": "job-101112",
  "status": "completed",
  "records_synced": 150000,
  "bytes_transferred": "2.3 GB",
  "duration_seconds": 900,
  "tables_created": ["iceberg.bronze.customers", "iceberg.bronze.transactions"]
}
```

### Testing Checklist

- [ ] Create data source (PostgreSQL/MySQL/API)
- [ ] Create S3 destination
- [ ] Start ingestion job
- [ ] Monitor job status until completion
- [ ] Verify tables created in Bronze layer
- [ ] Check record counts match source

---

## Spark Transformation APIs

### Overview

Spark APIs manage data transformations from Bronze to Silver layer using PySpark on Kubernetes.

### Check Spark Status

**Endpoint:** `GET /spark/status`

```bash
curl -X GET "$ASGARD_API/spark/status" | jq
```

**Response:**

```json
{
  "operator_status": "ready",
  "active_jobs": 2,
  "namespace": "asgard",
  "spark_version": "3.5.0"
}
```

### Submit Spark Transformation

**Endpoint:** `POST /spark/transform`

```bash
curl -X POST "$ASGARD_API/spark/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "customer_data_cleansing",
    "sql_query": "
      SELECT
        customer_id,
        TRIM(LOWER(email)) as email,
        COALESCE(first_name, '\''Unknown'\'') as first_name,
        CAST(registration_date as DATE) as registration_date,
        CURRENT_TIMESTAMP() as processed_at
      FROM iceberg.bronze.customers
      WHERE email IS NOT NULL
    ",
    "output_table": "iceberg.silver.customers_cleaned",
    "output_format": "iceberg",
    "partition_by": ["registration_date"],
    "mode": "overwrite"
  }' | jq
```

**Response:**

```json
{
  "run_id": "spark-run-001",
  "job_name": "customer_data_cleansing",
  "status": "submitted",
  "spark_app_name": "customer-data-cleansing-001",
  "driver_pod": "customer-data-cleansing-001-driver",
  "namespace": "asgard"
}
```

### Monitor Spark Job

**Endpoint:** `GET /spark/transform/{run_id}/status`

```bash
curl -X GET "$ASGARD_API/spark/transform/spark-run-001/status" | jq
```

**Response:**

```json
{
  "run_id": "spark-run-001",
  "status": "running",
  "driver_state": "RUNNING",
  "executor_state": "RUNNING",
  "application_state": {
    "state": "RUNNING"
  },
  "start_time": "2025-11-11T10:05:00Z"
}
```

### Get Spark Job Logs

**Endpoint:** `GET /spark/transform/{run_id}/logs`

```bash
curl -X GET "$ASGARD_API/spark/transform/spark-run-001/logs" | jq
```

### Get Spark Job Metrics

**Endpoint:** `GET /spark/transform/{run_id}/metrics`

```bash
curl -X GET "$ASGARD_API/spark/transform/spark-run-001/metrics" | jq
```

**Response:**

```json
{
  "run_id": "spark-run-001",
  "records_processed": 98500,
  "execution_time_seconds": 300,
  "input_size_bytes": 2400000000,
  "output_size_bytes": 1800000000
}
```

### List All Spark Jobs

**Endpoint:** `GET /spark/transform/jobs`

```bash
curl -X GET "$ASGARD_API/spark/transform/jobs?limit=10" | jq
```

### Testing Checklist

- [ ] Check Spark operator status
- [ ] Submit transformation job
- [ ] Monitor job status (wait for completion)
- [ ] Check logs for errors
- [ ] Verify metrics (records processed)
- [ ] Validate output table created
- [ ] Check data quality in Silver layer

---

## DBT Transformation APIs

### Overview

DBT APIs manage SQL-based transformations from Silver to Gold layer using Trino.

### Check DBT Status

**Endpoint:** `GET /dbt/status`

```bash
curl -X GET "$ASGARD_API/dbt/status" | jq
```

**Response:**

```json
{
  "trino_connection": "connected",
  "catalog": "iceberg",
  "models_count": 5,
  "last_run": "2025-11-11T09:00:00Z"
}
```

### Create DBT Transformation

**Endpoint:** `POST /dbt/transform`

```bash
curl -X POST "$ASGARD_API/dbt/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_metrics",
    "sql_query": "
      SELECT
        c.customer_id,
        c.email,
        COUNT(t.transaction_id) as total_purchases,
        SUM(t.amount) as customer_lifetime_value,
        AVG(t.amount) as avg_purchase_value,
        MAX(t.transaction_date) as last_purchase_date,
        CURRENT_TIMESTAMP as updated_at
      FROM iceberg.silver.customers_cleaned c
      LEFT JOIN iceberg.silver.transactions_cleaned t
        ON c.customer_id = t.customer_id
      GROUP BY c.customer_id, c.email
    ",
    "output_table": "iceberg.gold.customer_metrics",
    "description": "Customer behavioral metrics for ML",
    "materialized": "table",
    "tags": ["ml", "customer"]
  }' | jq
```

**Response:**

```json
{
  "transformation_id": "dbt-transform-001",
  "model_name": "customer_metrics",
  "status": "running",
  "output_table": "iceberg.gold.customer_metrics",
  "sql_validated": true,
  "estimated_rows": 98500
}
```

### Monitor DBT Transformation

**Endpoint:** `GET /dbt/transformations/{transformation_id}`

```bash
curl -X GET "$ASGARD_API/dbt/transformations/dbt-transform-001" | jq
```

**Response:**

```json
{
  "transformation_id": "dbt-transform-001",
  "status": "completed",
  "rows_created": 98500,
  "execution_time_seconds": 300,
  "output_table": "iceberg.gold.customer_metrics"
}
```

### List DBT Transformations

**Endpoint:** `GET /dbt/transformations`

```bash
curl -X GET "$ASGARD_API/dbt/transformations?page=1&page_size=20" | jq
```

### List Gold Layer Tables

**Endpoint:** `GET /dbt/gold-layer`

```bash
curl -X GET "$ASGARD_API/dbt/gold-layer" | jq
```

**Response:**

```json
{
  "tables": [
    {
      "name": "customer_metrics",
      "row_count": 98500,
      "size_bytes": 45000000,
      "created_at": "2025-11-11T10:15:00Z"
    }
  ]
}
```

### Get Table Stats

**Endpoint:** `GET /dbt/gold-layer/{table_name}/stats`

```bash
curl -X GET "$ASGARD_API/dbt/gold-layer/customer_metrics/stats" | jq
```

### Testing Checklist

- [ ] Check DBT/Trino status
- [ ] Submit transformation
- [ ] Monitor transformation status
- [ ] Verify SQL syntax validation
- [ ] Check rows created
- [ ] List gold layer tables
- [ ] Validate table stats

---

## Feast Feature Store APIs

### Overview

Feast APIs manage feature definitions and retrieval for ML workflows.

### Check Feast Status

**Endpoint:** `GET /feast/status`

```bash
curl -X GET "$ASGARD_API/feast/status" | jq
```

**Response:**

```json
{
  "registry_type": "sql",
  "store_type": "feast",
  "feature_views_count": 3,
  "entities_count": 2,
  "feature_services_count": 1,
  "feature_views": [
    "customer_churn_features",
    "product_features",
    "transaction_features"
  ]
}
```

### Register Feature View

**Endpoint:** `POST /feast/features`

```bash
curl -X POST "$ASGARD_API/feast/features" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_churn_features",
    "entity": {
      "name": "customer",
      "join_keys": ["customer_id"],
      "description": "Customer entity"
    },
    "features": [
      {"name": "total_purchases", "dtype": "int64"},
      {"name": "customer_lifetime_value", "dtype": "float64"},
      {"name": "avg_purchase_value", "dtype": "float64"},
      {"name": "days_since_last_purchase", "dtype": "int64"},
      {"name": "purchase_frequency", "dtype": "float64"},
      {"name": "account_age_days", "dtype": "int64"},
      {"name": "support_tickets", "dtype": "int64"},
      {"name": "churned", "dtype": "int64"}
    ],
    "timestamp_field": "updated_at",
    "source": {
      "type": "file",
      "path": "s3://airbytedestination1/iceberg/gold/customer_metrics/data/*.parquet",
      "timestamp_field": "updated_at"
    },
    "ttl": 86400,
    "tags": {"team": "ml", "use_case": "churn"}
  }' | jq
```

**Response:**

```json
{
  "feature_view_name": "customer_churn_features",
  "entity": "customer",
  "features_count": 8,
  "status": "registered",
  "created_at": "2025-11-11T11:00:00Z"
}
```

### List Feature Views

**Endpoint:** `GET /feast/features`

```bash
curl -X GET "$ASGARD_API/feast/features" | jq
```

**Response:**

```json
{
  "feature_views": [
    {
      "name": "customer_churn_features",
      "entities": ["customer"],
      "features": [
        "total_purchases",
        "customer_lifetime_value",
        "avg_purchase_value"
      ],
      "num_features": 8
    }
  ]
}
```

### Get Feature View Details

**Endpoint:** `GET /feast/features/{feature_view_name}`

```bash
curl -X GET "$ASGARD_API/feast/features/customer_churn_features" | jq
```

### Retrieve Historical Features

**Endpoint:** `POST /feast/features/historical`

```bash
curl -X POST "$ASGARD_API/feast/features/historical" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_service": "customer_churn_features",
    "entity_df": {
      "customer_id": [1001, 1002, 1003],
      "event_timestamp": [
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00"
      ]
    },
    "full_feature_names": false
  }' | jq
```

**Response:**

```json
{
  "features": [
    {
      "customer_id": 1001,
      "total_purchases": 25,
      "customer_lifetime_value": 3247.5,
      "avg_purchase_value": 129.9,
      "days_since_last_purchase": 5,
      "churned": 0
    }
  ],
  "row_count": 3
}
```

### Create Feature Service

**Endpoint:** `POST /feast/features/service`

```bash
curl -X POST "$ASGARD_API/feast/features/service" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "churn_prediction_service",
    "features": [
      "customer_churn_features:total_purchases",
      "customer_churn_features:customer_lifetime_value",
      "customer_churn_features:avg_purchase_value"
    ],
    "tags": {"owner": "ml-team"}
  }' | jq
```

### Testing Checklist

- [ ] Check Feast status
- [ ] Register feature view with entity
- [ ] List all feature views
- [ ] Get feature view details
- [ ] Test historical feature retrieval
- [ ] Create feature service
- [ ] Verify S3 path accessibility

---

## MLOps APIs

### Overview

MLOps APIs manage the complete ML lifecycle: training, model registry, and inference.

### Check MLOps Status

**Endpoint:** `GET /mlops/status`

```bash
curl -X GET "$ASGARD_API/mlops/status" | jq
```

**Response:**

```json
{
  "mlflow_tracking_uri": "http://mlflow-service:5000",
  "mlflow_available": true,
  "feast_store_available": true,
  "registered_models": 3,
  "active_experiments": 5,
  "feature_views": 3
}
```

### Upload Training Script

**Endpoint:** `POST /mlops/training/upload`

```bash
curl -X POST "$ASGARD_API/mlops/training/upload" \
  -F "file=@churn_training.py" \
  -F "experiment_name=customer_churn_prediction" \
  -F "run_name=random_forest_v1" \
  -F "requirements=scikit-learn==1.3.0,feast==0.35.0,pandas==2.0.3"
```

**Response:**

```json
{
  "job_id": "training-job-001",
  "status": "running",
  "experiment_name": "customer_churn_prediction",
  "run_name": "random_forest_v1",
  "mlflow_run_id": "abc123def456",
  "estimated_completion": "2025-11-11T11:30:00Z"
}
```

### Check Training Job Status

**Endpoint:** `GET /mlops/training/jobs/{job_id}`

```bash
curl -X GET "$ASGARD_API/mlops/training/jobs/training-job-001" | jq
```

**Response:**

```json
{
  "job_id": "training-job-001",
  "status": "completed",
  "metrics": {
    "accuracy": 0.875,
    "precision": 0.8234,
    "recall": 0.7891,
    "f1_score": 0.8058
  },
  "model_uri": "s3://bucket/mlruns/1/abc123def456/artifacts/model",
  "registered_model_name": "customer_churn_predictor",
  "model_version": 1
}
```

### Get Training Job Logs

**Endpoint:** `GET /mlops/training/jobs/{job_id}/logs`

```bash
curl -X GET "$ASGARD_API/mlops/training/jobs/training-job-001/logs"
```

### List Registered Models

**Endpoint:** `GET /mlops/models`

```bash
curl -X GET "$ASGARD_API/mlops/models" | jq
```

**Response:**

```json
{
  "models": [
    {
      "name": "customer_churn_predictor",
      "latest_version": 1,
      "creation_timestamp": "2025-11-11T11:30:00Z",
      "last_updated_timestamp": "2025-11-11T11:30:00Z"
    }
  ]
}
```

### Get Model Details

**Endpoint:** `GET /mlops/models/{model_name}`

```bash
curl -X GET "$ASGARD_API/mlops/models/customer_churn_predictor" | jq
```

**Response:**

```json
{
  "name": "customer_churn_predictor",
  "versions": [
    {
      "version": 1,
      "run_id": "abc123def456",
      "status": "READY",
      "creation_timestamp": "2025-11-11T11:30:00Z",
      "tags": {
        "model_type": "RandomForestClassifier",
        "accuracy": "0.8750"
      }
    }
  ]
}
```

### Make Predictions (Inference)

**Endpoint:** `POST /mlops/inference`

```bash
curl -X POST "$ASGARD_API/mlops/inference" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "model_version": 1,
    "inputs": [
      {
        "total_purchases": 5,
        "customer_lifetime_value": 450.00,
        "avg_purchase_value": 90.00,
        "days_since_last_purchase": 75,
        "purchase_frequency": 0.5,
        "account_age_days": 120,
        "support_tickets": 5,
        "avg_support_resolution_hours": 48.0
      }
    ]
  }' | jq
```

**Response:**

```json
{
  "model_name": "customer_churn_predictor",
  "model_version": 1,
  "predictions": [
    {
      "customer_index": 0,
      "churn_probability": 0.85,
      "prediction": 1,
      "risk_level": "high"
    }
  ],
  "inference_time_ms": 45
}
```

### Batch Inference

**Endpoint:** `POST /mlops/inference/batch`

```bash
curl -X POST "$ASGARD_API/mlops/inference/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "model_version": 1,
    "input_table": "iceberg.gold.customer_metrics",
    "output_table": "iceberg.gold.customer_churn_predictions",
    "batch_size": 1000
  }' | jq
```

### List Experiments

**Endpoint:** `GET /mlops/experiments`

```bash
curl -X GET "$ASGARD_API/mlops/experiments" | jq
```

### Testing Checklist

- [ ] Check MLOps status
- [ ] Upload training script
- [ ] Monitor training job
- [ ] Check training metrics
- [ ] List registered models
- [ ] Get model details
- [ ] Test real-time inference
- [ ] Test batch inference
- [ ] Verify model version tracking

---

## Data Products APIs

### Overview

Data Products APIs provide direct access to Iceberg tables for querying and validation.

### List All Tables

**Endpoint:** `GET /data-products`

```bash
curl -X GET "$ASGARD_API/data-products" | jq
```

**Response:**

```json
{
  "tables": [
    "iceberg.bronze.customers",
    "iceberg.silver.customers_cleaned",
    "iceberg.gold.customer_metrics"
  ]
}
```

### Query Table

**Endpoint:** `POST /data-products/query`

```bash
curl -X POST "$ASGARD_API/data-products/query" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "iceberg.gold.customer_metrics",
    "limit": 10
  }' | jq
```

**Response:**

```json
{
  "rows": [
    {
      "customer_id": 1001,
      "total_purchases": 25,
      "customer_lifetime_value": 3247.5
    }
  ],
  "row_count": 10
}
```

### Execute Custom SQL

```bash
curl -X POST "$ASGARD_API/data-products/query" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT COUNT(*) as total FROM iceberg.gold.customer_metrics WHERE churned = 1"
  }' | jq
```

### Get Table Schema

**Endpoint:** `GET /data-products/{table_name}/schema`

```bash
curl -X GET "$ASGARD_API/data-products/iceberg.gold.customer_metrics/schema" | jq
```

---

## Testing Tools

### cURL Examples

Create a script `test_apis.sh`:

```bash
#!/bin/bash
set -e

export ASGARD_API=http://localhost:8000

echo "1. Testing health..."
curl -s "$ASGARD_API/health" | jq '.status'

echo "2. Testing Airbyte..."
curl -s "$ASGARD_API/datasource" | jq '.sources | length'

echo "3. Testing Spark..."
curl -s "$ASGARD_API/spark/status" | jq '.operator_status'

echo "4. Testing DBT..."
curl -s "$ASGARD_API/dbt/status" | jq '.trino_connection'

echo "5. Testing Feast..."
curl -s "$ASGARD_API/feast/status" | jq '.feature_views_count'

echo "6. Testing MLOps..."
curl -s "$ASGARD_API/mlops/status" | jq '.mlflow_available'

echo "✅ All tests passed!"
```

### Python Client

```python
import requests
import json

class AsgardClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self):
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def create_datasource(self, config):
        response = requests.post(
            f"{self.base_url}/datasource",
            json=config
        )
        return response.json()

    def start_ingestion(self, source_id, dest_id, streams):
        config = {
            "sourceId": source_id,
            "destinationId": dest_id,
            "streams": streams
        }
        response = requests.post(
            f"{self.base_url}/ingestion",
            json=config
        )
        return response.json()

    def transform_spark(self, job_config):
        response = requests.post(
            f"{self.base_url}/spark/transform",
            json=job_config
        )
        return response.json()

    def register_features(self, feature_config):
        response = requests.post(
            f"{self.base_url}/feast/features",
            json=feature_config
        )
        return response.json()

    def train_model(self, script_path, experiment_name):
        with open(script_path, 'rb') as f:
            files = {'file': f}
            data = {'experiment_name': experiment_name}
            response = requests.post(
                f"{self.base_url}/mlops/training/upload",
                files=files,
                data=data
            )
        return response.json()

    def predict(self, model_name, version, inputs):
        config = {
            "model_name": model_name,
            "model_version": version,
            "inputs": inputs
        }
        response = requests.post(
            f"{self.base_url}/mlops/inference",
            json=config
        )
        return response.json()

# Usage
client = AsgardClient()
health = client.health_check()
print(f"Platform status: {health['status']}")
```

### Postman Collection

Import the following JSON into Postman:

```json
{
  "info": {
    "name": "Asgard Platform API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{BASE_URL}}/health"
      }
    },
    {
      "name": "Create Data Source",
      "request": {
        "method": "POST",
        "url": "{{BASE_URL}}/datasource",
        "body": {
          "mode": "raw",
          "raw": "{\n  \"source_type\": \"postgres\",\n  \"name\": \"test_db\"\n}"
        }
      }
    }
  ],
  "variable": [
    {
      "key": "BASE_URL",
      "value": "http://localhost:8000"
    }
  ]
}
```

---

## Complete Testing Workflow

### Step-by-Step Test Scenario

```bash
#!/bin/bash
# Complete end-to-end API testing workflow

export ASGARD_API=http://localhost:8000

echo "=== Phase 1: Data Ingestion ==="
# 1. Create data source
SOURCE_RESPONSE=$(curl -s -X POST "$ASGARD_API/datasource" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "postgres",
    "name": "test_customer_db",
    "source_config": {...}
  }')
SOURCE_ID=$(echo $SOURCE_RESPONSE | jq -r '.sourceId')
echo "Created source: $SOURCE_ID"

# 2. Start ingestion
JOB_RESPONSE=$(curl -s -X POST "$ASGARD_API/ingestion" \
  -H "Content-Type: application/json" \
  -d "{
    \"sourceId\": \"$SOURCE_ID\",
    \"destinationId\": \"dest-123\",
    \"streams\": [\"customers\"]
  }")
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.jobId')
echo "Started job: $JOB_ID"

# 3. Wait for completion
while true; do
  STATUS=$(curl -s "$ASGARD_API/ingestion/$JOB_ID/status" | jq -r '.status')
  echo "Job status: $STATUS"
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 10
done

echo "=== Phase 2: Data Cleansing ==="
# 4. Submit Spark job
SPARK_RESPONSE=$(curl -s -X POST "$ASGARD_API/spark/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "test_cleansing",
    "sql_query": "SELECT * FROM iceberg.bronze.customers WHERE email IS NOT NULL",
    "output_table": "iceberg.silver.customers_cleaned"
  }')
RUN_ID=$(echo $SPARK_RESPONSE | jq -r '.run_id')
echo "Started Spark job: $RUN_ID"

echo "=== Phase 3: Business Metrics ==="
# 5. Submit DBT transformation
DBT_RESPONSE=$(curl -s -X POST "$ASGARD_API/dbt/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "test_metrics",
    "sql_query": "SELECT customer_id, COUNT(*) as purchases FROM iceberg.silver.customers_cleaned GROUP BY customer_id",
    "output_table": "iceberg.gold.test_metrics"
  }')
echo "DBT transformation started"

echo "=== Phase 4: Feature Registration ==="
# 6. Register features
FEATURE_RESPONSE=$(curl -s -X POST "$ASGARD_API/feast/features" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_features",
    "entity": {"name": "customer", "join_keys": ["customer_id"]},
    "features": [{"name": "purchases", "dtype": "int64"}],
    "source": {"type": "file", "path": "s3://bucket/gold/test_metrics/data/*.parquet"}
  }')
echo "Features registered"

echo "=== Phase 5: Model Training ==="
# 7. Upload training script (assuming script exists)
# curl -X POST "$ASGARD_API/mlops/training/upload" -F "file=@test_training.py"

echo "=== Phase 6: Inference ==="
# 8. Make predictions (assuming model is trained)
# curl -X POST "$ASGARD_API/mlops/inference" -d '{...}'

echo "✅ Complete workflow tested successfully!"
```

---

## Summary

### API Endpoints by Category

| Category          | Endpoints                                | Primary Use        |
| ----------------- | ---------------------------------------- | ------------------ |
| **Airbyte**       | `/datasource`, `/datasink`, `/ingestion` | Data ingestion     |
| **Spark**         | `/spark/transform`, `/spark/status`      | Data cleansing     |
| **DBT**           | `/dbt/transform`, `/dbt/gold-layer`      | Business metrics   |
| **Feast**         | `/feast/features`, `/feast/status`       | Feature store      |
| **MLOps**         | `/mlops/training`, `/mlops/inference`    | ML lifecycle       |
| **Data Products** | `/data-products/query`                   | Direct data access |

### Testing Best Practices

1. **Start with health checks** - Always verify platform status first
2. **Test in sequence** - Follow the data flow: Airbyte → Spark → DBT → Feast → MLOps
3. **Monitor job status** - Wait for completion before proceeding
4. **Validate results** - Check record counts and data quality at each layer
5. **Use logs** - Check logs when jobs fail
6. **Test incrementally** - Test each phase separately before full workflow

### Next Steps

- **Learn more**: [USE_CASE_GUIDE.md](USE_CASE_GUIDE.md)
- **Troubleshoot**: [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
- **Understand architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
