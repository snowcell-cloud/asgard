# Asgard Platform - End-to-End Use Case Guide

**Complete Customer Churn Prediction Workflow**  
**Last Updated:** November 11, 2025  
**Version:** 1.0  
**Estimated Time:** 2-3 hours

---

## 📋 Table of Contents

1. [Use Case Overview](#use-case-overview)
2. [Business Context](#business-context)
3. [Data Requirements](#data-requirements)
4. [Phase 1: Data Ingestion (Airbyte)](#phase-1-data-ingestion-airbyte)
5. [Phase 2: Data Cleansing (Spark)](#phase-2-data-cleansing-spark)
6. [Phase 3: Business Aggregations (DBT)](#phase-3-business-aggregations-dbt)
7. [Phase 4: Feature Engineering (Feast)](#phase-4-feature-engineering-feast)
8. [Phase 5: ML Training (MLOps)](#phase-5-ml-training-mlops)
9. [Phase 6: Model Inference](#phase-6-model-inference)
10. [Validation & Monitoring](#validation--monitoring)
11. [Complete Python Example](#complete-python-example)

---

## Use Case Overview

### The Challenge

**Company:** E-commerce platform with 100,000+ active customers  
**Problem:** 15% monthly churn rate causing significant revenue loss  
**Goal:** Predict customers likely to churn in the next 30 days  
**Expected Outcome:** Reduce churn to 10% through proactive retention campaigns

### The Solution

Build an end-to-end ML pipeline using Asgard that:

1. Ingests customer and transaction data from multiple sources
2. Cleanses and standardizes the data
3. Creates business-level metrics and features
4. Trains a churn prediction model
5. Serves predictions via REST API

### The Data Flow

```
PostgreSQL      →  Airbyte  →  Bronze    →  Spark   →  Silver
  (Customers)       (Ingest)    (Raw)        (Clean)     (Validated)
                                                             ↓
MySQL           →  Airbyte  →  Bronze    →  Spark   →  Silver
  (Transactions)    (Ingest)    (Raw)        (Clean)     (Validated)
                                                             ↓
                                             DBT      →  Gold
                                           (Transform)   (Metrics)
                                                             ↓
                                            Feast     →  Features
                                          (Register)     (ML Ready)
                                                             ↓
                                            MLflow    →  Model
                                           (Train)      (Deployed)
```

---

## Business Context

### Current State

- **Customer Base:** 100,000 active customers
- **Monthly Churn:** 15% (15,000 customers/month)
- **Average Customer Lifetime Value:** $1,200
- **Monthly Revenue Loss:** $18M due to churn
- **Retention Campaign Cost:** $50 per customer

### Success Metrics

| Metric               | Current | Target       | Impact           |
| -------------------- | ------- | ------------ | ---------------- |
| **Churn Rate**       | 15%     | 10%          | 5% reduction     |
| **Customers Saved**  | 0       | 5,000/month  | +5,000 customers |
| **Revenue Retained** | $0      | $6M/month    | +$6M monthly     |
| **Campaign Cost**    | $0      | $250K/month  | -$250K expense   |
| **Net Benefit**      | $0      | $5.75M/month | **+$5.75M**      |

### ROI Calculation

- **Monthly Net Benefit:** $5.75M
- **Annual Benefit:** $69M
- **Platform Cost:** $200K/year
- **ROI:** **345x** return on investment

---

## Data Requirements

### Source Systems

#### 1. Customer Database (PostgreSQL)

**Tables:**

- `customers` - Customer profiles and demographics

**Key Columns:**

```sql
customer_id, email, first_name, last_name, registration_date,
status, country, city, created_at, updated_at
```

**Sample Data:**

```csv
customer_id,email,registration_date,status,country
1001,john@example.com,2024-01-15,active,US
1002,jane@example.com,2023-06-20,premium,UK
```

#### 2. Transaction System (MySQL)

**Tables:**

- `transactions` - Order history and purchase data

**Key Columns:**

```sql
transaction_id, customer_id, order_id, amount, transaction_date,
payment_method, status, created_at
```

**Sample Data:**

```csv
transaction_id,customer_id,amount,transaction_date,status
5001,1001,129.99,2025-11-10,completed
5002,1001,49.99,2025-10-15,completed
```

#### 3. Support System (API)

**Endpoint:** `/api/v1/tickets`

**Key Fields:**

```json
{
  "ticket_id": 7001,
  "customer_id": 1001,
  "created_at": "2025-11-01T10:00:00Z",
  "resolution_time_hours": 24,
  "satisfaction_score": 4
}
```

### ML Features

| Feature                        | Description                 | Source       | Type    |
| ------------------------------ | --------------------------- | ------------ | ------- |
| `total_purchases`              | Total number of orders      | Transactions | Integer |
| `customer_lifetime_value`      | Total revenue from customer | Transactions | Decimal |
| `avg_purchase_value`           | Average order value         | Transactions | Decimal |
| `days_since_last_purchase`     | Recency of last order       | Transactions | Integer |
| `purchase_frequency`           | Orders per month            | Transactions | Decimal |
| `account_age_days`             | Customer tenure             | Customers    | Integer |
| `support_tickets`              | Number of support requests  | Support API  | Integer |
| `avg_support_resolution_hours` | Avg ticket resolution time  | Support API  | Decimal |

### Target Variable

- **`churned`**: Binary (0 = retained, 1 = churned)
- **Definition:** Customer with no purchases in the last 60 days

---

## Phase 1: Data Ingestion (Airbyte)

### Objective

Ingest raw data from source systems into the Bronze layer of the data lakehouse.

### Timeline

⏱️ **Setup Time:** 30 minutes  
⏱️ **Sync Time:** 15 minutes (for 150K records)

### Steps

#### 1.1 Create PostgreSQL Data Source

```bash
curl -X POST http://localhost:8000/datasource \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "postgres",
    "workspace_name": "default",
    "name": "customer_database",
    "source_config": {
      "host": "customer-db.example.com",
      "port": 5432,
      "database": "customers",
      "username": "readonly_user",
      "password": "secure_password",
      "schemas": ["public"]
    }
  }'
```

**Expected Response:**

```json
{
  "sourceId": "abc123-source-456",
  "name": "customer_database",
  "status": "active",
  "streams_available": ["customers", "addresses", "preferences"],
  "created_at": "2025-11-11T10:00:00Z"
}
```

#### 1.2 Create MySQL Data Source

```bash
curl -X POST http://localhost:8000/datasource \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mysql",
    "workspace_name": "default",
    "name": "transaction_system",
    "source_config": {
      "host": "transactions-db.example.com",
      "port": 3306,
      "database": "orders",
      "username": "etl_user",
      "password": "secure_password"
    }
  }'
```

#### 1.3 Create S3/Iceberg Destination

```bash
curl -X POST http://localhost:8000/datasink \
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
  }'
```

#### 1.4 Start Data Ingestion

```bash
curl -X POST http://localhost:8000/ingestion \
  -H "Content-Type: application/json" \
  -d '{
    "sourceId": "abc123-source-456",
    "destinationId": "xyz789-dest-012",
    "streams": [
      "customers",
      "transactions",
      "support_tickets"
    ],
    "schedule": {
      "scheduleType": "cron",
      "cronExpression": "0 */6 * * *"
    }
  }'
```

**Expected Response:**

```json
{
  "connectionId": "conn-789",
  "jobId": "job-101112",
  "status": "running",
  "records_synced": 0,
  "estimated_completion": "2025-11-11T10:30:00Z"
}
```

### Validation

```bash
# Check ingestion status
curl http://localhost:8000/ingestion/job-101112/status | jq

# Expected output
{
  "status": "completed",
  "records_synced": 150000,
  "bytes_transferred": "2.3 GB",
  "tables_created": [
    "iceberg.bronze.customers",
    "iceberg.bronze.transactions",
    "iceberg.bronze.support_tickets"
  ],
  "duration_seconds": 900
}
```

### Result

✅ **Bronze Layer Created**

- **Table:** `iceberg.bronze.customers` - 100,000 rows
- **Table:** `iceberg.bronze.transactions` - 1,200,000 rows
- **Table:** `iceberg.bronze.support_tickets` - 45,000 rows
- **Storage:** `s3://airbytedestination1/iceberg/bronze/`
- **Format:** Parquet (Snappy compression)

---

## Phase 2: Data Cleansing (Spark)

### Objective

Clean, validate, and standardize data from Bronze to Silver layer using PySpark on Kubernetes.

### Timeline

⏱️ **Job Setup:** 5 minutes  
⏱️ **Execution Time:** 10 minutes (for 150K records)

### Steps

#### 2.1 Clean Customer Data

```bash
curl -X POST http://localhost:8000/spark/transform \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "customer_data_cleansing",
    "sql_query": "
      SELECT
        customer_id,
        TRIM(LOWER(email)) as email,
        COALESCE(first_name, '\''Unknown'\'') as first_name,
        COALESCE(last_name, '\''Unknown'\'') as last_name,
        CAST(registration_date as DATE) as registration_date,
        CASE
          WHEN status IN ('\''active'\'', '\''premium'\'') THEN status
          ELSE '\''inactive'\''
        END as status,
        UPPER(country) as country,
        CAST(created_at as TIMESTAMP) as created_at,
        CURRENT_TIMESTAMP() as processed_at
      FROM iceberg.bronze.customers
      WHERE email IS NOT NULL
        AND email LIKE '\''%@%'\''
        AND registration_date >= '\''2020-01-01'\''
    ",
    "output_table": "iceberg.silver.customers_cleaned",
    "output_format": "iceberg",
    "partition_by": ["country", "registration_date"],
    "mode": "overwrite"
  }'
```

**Expected Response:**

```json
{
  "run_id": "spark-run-001",
  "job_name": "customer_data_cleansing",
  "status": "submitted",
  "spark_app_name": "customer-data-cleansing-001",
  "namespace": "asgard",
  "driver_pod": "customer-data-cleansing-001-driver",
  "tracking_url": "http://spark-ui:4040"
}
```

#### 2.2 Clean Transaction Data

```bash
curl -X POST http://localhost:8000/spark/transform \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "transaction_data_cleansing",
    "sql_query": "
      SELECT
        transaction_id,
        customer_id,
        order_id,
        CAST(amount as DECIMAL(10,2)) as amount,
        CAST(transaction_date as DATE) as transaction_date,
        LOWER(payment_method) as payment_method,
        LOWER(status) as status,
        CAST(created_at as TIMESTAMP) as created_at,
        CURRENT_TIMESTAMP() as processed_at
      FROM iceberg.bronze.transactions
      WHERE amount > 0
        AND customer_id IS NOT NULL
        AND transaction_date >= '\''2023-01-01'\''
        AND status = '\''completed'\''
    ",
    "output_table": "iceberg.silver.transactions_cleaned",
    "output_format": "iceberg",
    "partition_by": ["transaction_date"],
    "mode": "append"
  }'
```

#### 2.3 Monitor Spark Jobs

```bash
# Check job status
curl http://localhost:8000/spark/transform/spark-run-001/status | jq

# View logs
curl http://localhost:8000/spark/transform/spark-run-001/logs

# Get metrics
curl http://localhost:8000/spark/transform/spark-run-001/metrics | jq
```

### Validation

```bash
# List all Spark jobs
curl http://localhost:8000/spark/transform/jobs?limit=10 | jq

# Verify row counts
curl -X POST http://localhost:8000/data-products/query \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "iceberg.silver.customers_cleaned",
    "sql": "SELECT COUNT(*) as row_count FROM iceberg.silver.customers_cleaned"
  }' | jq
```

### Result

✅ **Silver Layer Created**

- **Table:** `iceberg.silver.customers_cleaned` - 98,500 rows (1,500 invalid emails removed)
- **Table:** `iceberg.silver.transactions_cleaned` - 1,180,000 rows (20,000 invalid transactions removed)
- **Storage:** `s3://airbytedestination1/iceberg/silver/`
- **Data Quality:** Email validation, null handling, type casting complete

---

## Phase 3: Business Aggregations (DBT)

### Objective

Create business-level aggregated metrics in the Gold layer using SQL transformations.

### Timeline

⏱️ **Model Creation:** 10 minutes  
⏱️ **Execution Time:** 5 minutes

### Steps

#### 3.1 Create Customer Metrics Model

```bash
curl -X POST http://localhost:8000/dbt/transform \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_metrics",
    "sql_query": "
      WITH customer_orders AS (
        SELECT
          c.customer_id,
          c.email,
          c.registration_date,
          c.country,
          c.status,
          COUNT(t.transaction_id) as total_purchases,
          COALESCE(SUM(t.amount), 0) as customer_lifetime_value,
          COALESCE(AVG(t.amount), 0) as avg_purchase_value,
          MAX(t.transaction_date) as last_purchase_date,
          MIN(t.transaction_date) as first_purchase_date
        FROM iceberg.silver.customers_cleaned c
        LEFT JOIN iceberg.silver.transactions_cleaned t
          ON c.customer_id = t.customer_id
        GROUP BY c.customer_id, c.email, c.registration_date, c.country, c.status
      ),
      customer_support AS (
        SELECT
          customer_id,
          COUNT(*) as support_tickets,
          AVG(COALESCE(resolution_time_hours, 0)) as avg_resolution_time
        FROM iceberg.silver.support_tickets_cleaned
        GROUP BY customer_id
      )
      SELECT
        co.customer_id,
        co.email,
        co.total_purchases,
        co.customer_lifetime_value,
        co.avg_purchase_value,
        DATE_DIFF('\''day'\'', co.last_purchase_date, CURRENT_DATE) as days_since_last_purchase,
        DATE_DIFF('\''day'\'', co.registration_date, CURRENT_DATE) as account_age_days,
        CASE
          WHEN co.total_purchases = 0 THEN 0
          ELSE CAST(co.total_purchases as DOUBLE) / NULLIF(
            CAST(DATE_DIFF('\''day'\'', co.first_purchase_date, CURRENT_DATE) as DOUBLE) / 30.0, 0
          )
        END as purchase_frequency,
        COALESCE(cs.support_tickets, 0) as support_tickets,
        COALESCE(cs.avg_resolution_time, 0) as avg_support_resolution_hours,
        co.country,
        co.status,
        CASE
          WHEN DATE_DIFF('\''day'\'', co.last_purchase_date, CURRENT_DATE) > 60 THEN 1
          ELSE 0
        END as churned,
        CURRENT_TIMESTAMP as updated_at
      FROM customer_orders co
      LEFT JOIN customer_support cs
        ON co.customer_id = cs.customer_id
    ",
    "output_table": "iceberg.gold.customer_metrics",
    "description": "Customer behavioral and transactional metrics for ML",
    "materialized": "table",
    "tags": ["ml", "churn", "customer"]
  }'
```

**Expected Response:**

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

#### 3.2 Monitor DBT Transformation

```bash
# Check transformation status
curl http://localhost:8000/dbt/transformations/dbt-transform-001 | jq

# Expected output
{
  "transformation_id": "dbt-transform-001",
  "status": "completed",
  "rows_created": 98500,
  "execution_time_seconds": 300,
  "output_table": "iceberg.gold.customer_metrics"
}
```

### Validation

```bash
# List gold layer tables
curl http://localhost:8000/dbt/gold-layer | jq

# Get table stats
curl http://localhost:8000/dbt/gold-layer/customer_metrics/stats | jq

# Preview data
curl -X POST http://localhost:8000/data-products/query \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "iceberg.gold.customer_metrics",
    "limit": 5
  }' | jq
```

### Result

✅ **Gold Layer Created**

- **Table:** `iceberg.gold.customer_metrics` - 98,500 rows
- **Features:** 13 ML-ready features per customer
- **Target Variable:** `churned` (binary classification)
- **Storage:** `s3://airbytedestination1/iceberg/gold/`

---

## Phase 4: Feature Engineering (Feast)

### Objective

Register features in Feast feature store for ML model consumption.

### Timeline

⏱️ **Feature Registration:** 5 minutes  
⏱️ **Historical Retrieval:** 2 minutes

### Steps

#### 4.1 Register Feature View

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_churn_features",
    "entity": {
      "name": "customer",
      "join_keys": ["customer_id"],
      "description": "Customer entity for churn prediction"
    },
    "features": [
      {"name": "total_purchases", "dtype": "int64"},
      {"name": "customer_lifetime_value", "dtype": "float64"},
      {"name": "avg_purchase_value", "dtype": "float64"},
      {"name": "days_since_last_purchase", "dtype": "int64"},
      {"name": "purchase_frequency", "dtype": "float64"},
      {"name": "account_age_days", "dtype": "int64"},
      {"name": "support_tickets", "dtype": "int64"},
      {"name": "avg_support_resolution_hours", "dtype": "float64"},
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
  }'
```

**Expected Response:**

```json
{
  "feature_view_name": "customer_churn_features",
  "entity": "customer",
  "features_count": 9,
  "status": "registered",
  "created_at": "2025-11-11T11:00:00Z"
}
```

#### 4.2 Verify Feature Registration

```bash
# Get feature store status
curl http://localhost:8000/feast/status | jq

# List all feature views
curl http://localhost:8000/feast/features | jq
```

#### 4.3 Retrieve Historical Features

```bash
curl -X POST http://localhost:8000/feast/features/historical \
  -H "Content-Type: application/json" \
  -d '{
    "feature_service": "customer_churn_features",
    "entity_df": {
      "customer_id": [1001, 1002, 1003, 1004, 1005],
      "event_timestamp": [
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00",
        "2025-11-11T00:00:00"
      ]
    },
    "full_feature_names": false
  }'
```

**Expected Response:**

```json
{
  "features": [
    {
      "customer_id": 1001,
      "total_purchases": 25,
      "customer_lifetime_value": 3247.5,
      "avg_purchase_value": 129.9,
      "days_since_last_purchase": 5,
      "purchase_frequency": 2.5,
      "account_age_days": 450,
      "support_tickets": 2,
      "avg_support_resolution_hours": 18.5,
      "churned": 0
    }
  ],
  "row_count": 5
}
```

### Result

✅ **Feature Store Ready**

- **Feature View:** `customer_churn_features` registered
- **Features:** 9 ML features available
- **Entity:** `customer` with `customer_id` as join key
- **Source:** Direct S3 Parquet read (no duplication!)

---

## Phase 5: ML Training (MLOps)

### Objective

Train a churn prediction model using features from Feast and track with MLflow.

### Timeline

⏱️ **Script Upload:** 2 minutes  
⏱️ **Training Time:** 15 minutes

### Steps

#### 5.1 Create Training Script

Create `churn_training.py`:

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import mlflow
import mlflow.sklearn
from feast import FeatureStore
import os

# Initialize Feast
store = FeatureStore(repo_path="/app/feast_repo")

# Get training data from Feast
entity_df = pd.read_parquet("s3://bucket/entity_df.parquet")
training_df = store.get_historical_features(
    entity_df=entity_df,
    features=["customer_churn_features:total_purchases",
              "customer_churn_features:customer_lifetime_value",
              "customer_churn_features:avg_purchase_value",
              "customer_churn_features:days_since_last_purchase",
              "customer_churn_features:purchase_frequency",
              "customer_churn_features:account_age_days",
              "customer_churn_features:support_tickets",
              "customer_churn_features:avg_support_resolution_hours",
              "customer_churn_features:churned"]
).to_df()

# Prepare features and target
X = training_df.drop(columns=["customer_id", "event_timestamp", "churned"])
y = training_df["churned"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Start MLflow run
mlflow.set_tracking_uri("http://mlflow-service:5000")
mlflow.set_experiment("customer_churn_prediction")

with mlflow.start_run(run_name="random_forest_v1"):
    # Log parameters
    mlflow.log_param("model_type", "RandomForestClassifier")
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("test_size", len(X_test))

    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)
    mlflow.log_metric("f1_score", f1)

    # Log model
    mlflow.sklearn.log_model(
        model,
        "model",
        registered_model_name="customer_churn_predictor"
    )

    print(f"Model trained successfully!")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
```

#### 5.2 Upload and Execute Training Script

```bash
curl -X POST http://localhost:8000/mlops/training/upload \
  -F "file=@churn_training.py" \
  -F "experiment_name=customer_churn_prediction" \
  -F "run_name=random_forest_v1" \
  -F "requirements=scikit-learn==1.3.0,feast==0.35.0,pandas==2.0.3"
```

**Expected Response:**

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

#### 5.3 Monitor Training Job

```bash
# Check job status
curl http://localhost:8000/mlops/training/jobs/training-job-001 | jq

# View logs
curl http://localhost:8000/mlops/training/jobs/training-job-001/logs

# Get metrics
curl http://localhost:8000/mlops/training/jobs/training-job-001/metrics | jq
```

**Expected Output:**

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

### Result

✅ **Model Trained and Registered**

- **Model:** `customer_churn_predictor` v1
- **Accuracy:** 87.5%
- **F1 Score:** 80.58%
- **Status:** Registered in MLflow Model Registry
- **Artifacts:** Stored in S3

---

## Phase 6: Model Inference

### Objective

Deploy model and make predictions on new customer data.

### Timeline

⏱️ **Deployment:** 2 minutes  
⏱️ **Inference:** Real-time (<100ms per request)

### Steps

#### 6.1 Make Predictions

```bash
curl -X POST http://localhost:8000/mlops/inference \
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
      },
      {
        "total_purchases": 45,
        "customer_lifetime_value": 5200.00,
        "avg_purchase_value": 115.56,
        "days_since_last_purchase": 3,
        "purchase_frequency": 3.2,
        "account_age_days": 890,
        "support_tickets": 1,
        "avg_support_resolution_hours": 12.0
      }
    ]
  }'
```

**Expected Response:**

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
    },
    {
      "customer_index": 1,
      "churn_probability": 0.12,
      "prediction": 0,
      "risk_level": "low"
    }
  ],
  "inference_time_ms": 45
}
```

#### 6.2 Batch Predictions

```bash
curl -X POST http://localhost:8000/mlops/inference/batch \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "customer_churn_predictor",
    "model_version": 1,
    "input_table": "iceberg.gold.customer_metrics",
    "output_table": "iceberg.gold.customer_churn_predictions",
    "batch_size": 1000
  }'
```

### Result

✅ **Model Deployed and Serving**

- **Inference API:** Available at `/mlops/inference`
- **Response Time:** <100ms per prediction
- **Batch Processing:** Supported for large-scale predictions
- **Model Version:** Tracked and versioned in MLflow

---

## Validation & Monitoring

### Data Validation

```bash
# Verify row counts across layers
echo "Bronze layer:"
curl -X POST http://localhost:8000/data-products/query \
  -d '{"sql":"SELECT COUNT(*) FROM iceberg.bronze.customers"}' | jq

echo "Silver layer:"
curl -X POST http://localhost:8000/data-products/query \
  -d '{"sql":"SELECT COUNT(*) FROM iceberg.silver.customers_cleaned"}' | jq

echo "Gold layer:"
curl -X POST http://localhost:8000/data-products/query \
  -d '{"sql":"SELECT COUNT(*) FROM iceberg.gold.customer_metrics"}' | jq
```

### Model Monitoring

```bash
# Get model performance
curl http://localhost:8000/mlops/models/customer_churn_predictor/metrics | jq

# Check prediction distribution
curl -X POST http://localhost:8000/data-products/query \
  -d '{
    "sql": "SELECT prediction, COUNT(*) as count FROM iceberg.gold.customer_churn_predictions GROUP BY prediction"
  }' | jq
```

### Pipeline Health

```bash
# Check all services
curl http://localhost:8000/health | jq

# Check Feast status
curl http://localhost:8000/feast/status | jq

# Check MLflow experiments
curl http://localhost:8000/mlops/experiments | jq
```

---

## Complete Python Example

Here's a complete Python script that runs the entire workflow:

```python
import requests
import time
import json

BASE_URL = "http://localhost:8000"

class AsgardClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def create_datasource(self, config):
        """Phase 1: Create data source"""
        response = requests.post(f"{self.base_url}/datasource", json=config)
        return response.json()

    def start_ingestion(self, source_id, dest_id, streams):
        """Phase 1: Start data ingestion"""
        config = {
            "sourceId": source_id,
            "destinationId": dest_id,
            "streams": streams
        }
        response = requests.post(f"{self.base_url}/ingestion", json=config)
        return response.json()

    def transform_spark(self, job_config):
        """Phase 2: Spark transformation"""
        response = requests.post(f"{self.base_url}/spark/transform", json=job_config)
        return response.json()

    def transform_dbt(self, model_config):
        """Phase 3: DBT transformation"""
        response = requests.post(f"{self.base_url}/dbt/transform", json=model_config)
        return response.json()

    def register_features(self, feature_config):
        """Phase 4: Register features"""
        response = requests.post(f"{self.base_url}/feast/features", json=feature_config)
        return response.json()

    def upload_training_script(self, script_path, experiment_name):
        """Phase 5: Upload and run training"""
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
        """Phase 6: Make predictions"""
        config = {
            "model_name": model_name,
            "model_version": version,
            "inputs": inputs
        }
        response = requests.post(f"{self.base_url}/mlops/inference", json=config)
        return response.json()

    def wait_for_job(self, job_id, job_type="ingestion"):
        """Wait for job completion"""
        while True:
            response = requests.get(f"{self.base_url}/{job_type}/jobs/{job_id}")
            status = response.json()
            if status["status"] in ["completed", "failed"]:
                return status
            time.sleep(10)

# Usage example
client = AsgardClient(BASE_URL)

# Phase 1: Ingest data
print("Phase 1: Starting data ingestion...")
source = client.create_datasource({
    "source_type": "postgres",
    "name": "customer_db",
    "source_config": {...}
})
job = client.start_ingestion(source["sourceId"], "dest-123", ["customers"])
print(f"Ingestion job started: {job['jobId']}")

# Wait for completion
print("Waiting for ingestion to complete...")
result = client.wait_for_job(job["jobId"])
print(f"Ingestion complete: {result['records_synced']} records")

# Phase 2: Clean data
print("\nPhase 2: Cleaning data with Spark...")
spark_job = client.transform_spark({
    "job_name": "customer_cleansing",
    "sql_query": "SELECT * FROM iceberg.bronze.customers WHERE email IS NOT NULL",
    "output_table": "iceberg.silver.customers_cleaned"
})
print(f"Spark job started: {spark_job['run_id']}")

# Phase 3: Create aggregations
print("\nPhase 3: Creating business metrics...")
dbt_job = client.transform_dbt({
    "model_name": "customer_metrics",
    "sql_query": "SELECT customer_id, COUNT(*) as purchases FROM ...",
    "output_table": "iceberg.gold.customer_metrics"
})
print(f"DBT transformation started: {dbt_job['transformation_id']}")

# Phase 4: Register features
print("\nPhase 4: Registering features...")
features = client.register_features({
    "name": "customer_churn_features",
    "entity": {"name": "customer", "join_keys": ["customer_id"]},
    "features": [...]
})
print(f"Features registered: {features['feature_view_name']}")

# Phase 5: Train model
print("\nPhase 5: Training ML model...")
training = client.upload_training_script(
    "churn_training.py",
    "customer_churn_prediction"
)
print(f"Training started: {training['job_id']}")

# Wait for training
print("Waiting for training to complete...")
training_result = client.wait_for_job(training["job_id"], "mlops/training")
print(f"Model trained: {training_result['metrics']}")

# Phase 6: Make predictions
print("\nPhase 6: Making predictions...")
predictions = client.predict(
    "customer_churn_predictor",
    1,
    [{"total_purchases": 5, "customer_lifetime_value": 450.00, ...}]
)
print(f"Predictions: {predictions}")

print("\n✅ Complete workflow finished successfully!")
```

---

## Summary

### What You've Accomplished

1. ✅ Ingested data from multiple sources into Bronze layer
2. ✅ Cleaned and validated data into Silver layer
3. ✅ Created business metrics in Gold layer
4. ✅ Registered ML features in Feast
5. ✅ Trained a churn prediction model with 87.5% accuracy
6. ✅ Deployed model for real-time inference

### Next Steps

1. **Set up monitoring** - Track model performance over time
2. **Create retention campaigns** - Use predictions to target high-risk customers
3. **Iterate on features** - Add more features to improve accuracy
4. **Scale the pipeline** - Process millions of customers
5. **Deploy to production** - Set up automated retraining

### Resources

- **API Testing**: [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
- **Debugging**: [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Diagrams**: [DIAGRAMS.md](DIAGRAMS.md)

**🎉 Congratulations!** You've completed a full end-to-end ML workflow with Asgard!
