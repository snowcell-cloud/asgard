# Asgard Platform

**Unified ML Data Platform: From Raw Data to Deployed Models**

**Version:** 3.0.0  
**Last Updated:** November 14, 2025

---

## Platform Overview

### What is Asgard?

Asgard is a **unified, API-driven ML data platform** that orchestrates the complete lifecycle from raw data ingestion to production ML model deployment. It implements the **Medallion Architecture** (Bronze → Silver → Gold) using best-in-class open-source tools.

### Key Principles

- **Single API Gateway**: All operations through one FastAPI endpoint
- **Zero Data Duplication**: Direct reads from Iceberg S3 Parquet storage
- **Kubernetes Native**: Production-ready, auto-scaling, cloud-agnostic
- **Open Source Stack**: Built on proven tools (Airbyte, Spark, DBT, Feast, MLflow)
- **API-Driven**: No manual configuration files or cron jobs

### Technology Stack

| Layer               | Tool                        | Purpose                                 |
| ------------------- | --------------------------- | --------------------------------------- |
| **Data Ingestion**  | Airbyte                     | ELT from sources to S3                  |
| **Data Processing** | Apache Spark + K8s Operator | Distributed SQL transformations         |
| **Feature Eng.**    | DBT + Trino                 | SQL-based feature creation (Gold layer) |
| **Feature Store**   | Feast + Iceberg             | Feature serving from S3 Parquet         |
| **ML Training**     | MLflow + Scikit/XGBoost/etc | Model training, tracking, registry      |
| **ML Deployment**   | Kaniko + Kubernetes         | Containerized model serving             |
| **Storage**         | Iceberg + Nessie + S3       | Data lakehouse with version control     |
| **Query Engine**    | Trino                       | Distributed SQL on Iceberg              |
| **Orchestration**   | Kubernetes + FastAPI        | Container orchestration & API gateway   |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ASGARD DATA PLATFORM                                   |
│                    FastAPI Gateway (Port 8000/80)                               |
│                                                                                 |
|                                                                                 |
└────────────┬────────────────────────────────────────────────────────────────────┘
             │
             │
┌────────────┴────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  Layer 1: DATA INGESTION (Airbyte)                  Storage: S3 Bronze Layer    │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│  External Sources → Airbyte Connectors → S3 (Bronze)                            │
│  - PostgreSQL/MySQL/APIs                                                         │
│  - REST APIs                                 s3://bucket/bronze/
                                                ├── customers/*.parquet           │
│                                               ├── transactions/*.parquet        │
│                                                └── support_tickets/*.parquet     │
│  Airbyte Client → HTTP API                                                       │
│  - Create sources                            Format: Parquet                     │
│  - Create destinations (S3/Iceberg)          Catalog: Iceberg + Nessie          │
│  - Schedule syncs (cron)                     Compression: Snappy                 │
│                                                                                   │
│  Endpoints:                                  Data Characteristics:               │
│  POST /datasource    - Register source       - Raw, unfiltered data             │
│  POST /sink          - Register S3 dest      - Schema preserved from source     │
│  POST /ingestion     - Create connection     - Incremental sync supported       │
│  GET  /datasource    - List sources          - Change Data Capture (CDC)        │
│  GET  /sink          - List destinations                                         │
│  GET  /ingestion/{id}/status - Check sync                                        │
│                                                                                   │
└────────────┬────────────────────────────────────────────────────────────────────┘
             │
             ▼ Bronze → Silver
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  Layer 2: DATA TRANSFORMATION (Spark)           Storage: S3 Silver Layer        │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│  Spark Jobs (Kubernetes Operator)                                               │
│  - Driver Pod + Executor Pods               s3://bucket/silver/{run_id}/        │
│  - Custom Spark Image with Iceberg           ├── cleaned_customers/             │
│  - S3A connector for direct S3 access        ├── filtered_transactions/         │
│  - Dynamic SQL execution                     └── processed_tickets/             │
│                                                                                   │
│  SparkApplication CRD                        Also writes to:                     │
│  apiVersion: sparkoperator.k8s.io/v1beta2   Iceberg Tables (via Nessie)        │
│  kind: SparkApplication                      iceberg.silver.table_name          │
│                                                                                   │
│  Transformation Pipeline:                    Data Characteristics:               │
│  1. Read from Bronze (Parquet)               - Cleaned & validated              │
│  2. Execute SQL transformation               - Type conversions applied         │
│  3. Write to Silver (Parquet)                - Null handling                    │
│  4. Optionally write to Iceberg              - Deduplication                    │
│                                               - Basic enrichment                 │
│  Endpoints:                                                                       │
│  POST /spark/transform           - Submit job (SQL query)                       │
│  GET  /spark/transform/{id}/status - Check job status                           │
│  GET  /spark/transform/{id}/logs   - Get Spark logs                             │
│                                                                                   │
│  SQL Example:                                                                     │
│  SELECT customer_id, LOWER(email) as email,                                     │
│         CAST(amount as DECIMAL(10,2)) as amount                                 │
│  FROM source_data WHERE email IS NOT NULL                                       │
│                                                                                   │
└────────────┬────────────────────────────────────────────────────────────────────┘
             │
             ▼ Silver → Gold
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  Layer 3: FEATURE ENGINEERING (DBT + Trino)     Storage: S3 Gold Layer         │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│  DBT Transformations (API-triggered)                                            │
│  - Dynamic model generation                 Iceberg Catalog (Nessie):          │
│  - Trino execution engine                   iceberg.gold.customer_features     │
│  - SQL-based feature creation               iceberg.gold.transaction_agg       │
│  - Automatic materialization                iceberg.gold.ml_ready_features     │
│                                                                                   │
│  DBT Project Structure:                      S3 Physical Storage:                │
│  /tmp/dbt_project/                          s3://bucket/iceberg/gold/          │
│    ├── dbt_project.yml                       ├── customer_features/            │
│    ├── profiles.yml (Trino connection)       │   ├── data/*.parquet           │
│    └── models/gold/{model_name}.sql          │   └── metadata/                │
│                                               └── transaction_agg/              │
│  profiles.yml:                                    ├── data/*.parquet           │
│    target: trino                                  └── metadata/                │
│    host: trino.data-platform.svc.cluster.local                                 │
│    catalog: iceberg                          Data Characteristics:               │
│    schema: gold                              - Business-ready aggregations      │
│    port: 8080                                - Feature engineering applied      │
│                                               - ML-ready format                  │
│  Transformation Flow:                        - Time-based features               │
│  1. User submits SQL via API                 - Categorical encodings            │
│  2. Generate .sql model file                 - Derived metrics                  │
│  3. Execute: dbt run --select model                                              │
│  4. Create Iceberg table in Gold                                                 │
│                                                                                   │
│  Endpoints:                                                                       │
│  POST /dbt/transform              - Create transformation                       │
│  GET  /dbt/transformations        - List transformations                        │
│  GET  /dbt/transformations/{id}   - Get transformation details                  │
│  GET  /dbt/sources/silver         - List available Silver tables                │
│  GET  /dbt/tables/gold            - List Gold layer tables                      │
│                                                                                   │
│  SQL Example (Feature Engineering):                                              │
│  SELECT                                                                           │
│    customer_id,                                                                   │
│    COUNT(*) as total_orders,                                                     │
│    SUM(amount) as total_spent,                                                   │
│    AVG(amount) as avg_order_value,                                               │
│    DATEDIFF('day', MAX(order_date), CURRENT_DATE) as days_since_last_order     │
│  FROM iceberg.silver.transactions_cleaned                                        │
│  GROUP BY customer_id                                                             │
│                                                                                   │
└────────────┬────────────────────────────────────────────────────────────────────┘
             │
             ▼ Features → Feature Store
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  Layer 4: FEATURE STORE (Feast + Iceberg)       Storage: Direct S3 Read        │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│  Feast FeatureStore                                                              │
│  - Registry: SQLite (local metadata)        Zero Data Duplication!             │
│  - Offline Store: File (S3 Parquet)         Feast reads directly from:         │
│  - Online Store: DISABLED (offline only)    s3://bucket/iceberg/gold/*/data/   │
│                                                                                   │
│  Feature Registration Flow:                 How it Works:                        │
│  1. User creates feature view via API       1. Query Trino for table metadata   │
│  2. Service queries Trino to validate       2. Extract S3 Parquet path          │
│     iceberg.gold.table_name exists          3. Create Feast FileSource          │
│  3. Extract S3 path from Iceberg metadata      pointing to S3 path              │
│  4. Create Feast FileSource with S3 path    4. Register with Feast registry     │
│  5. Register entities and feature view      5. NO data sync/copy needed         │
│                                                                                   │
│  Feature View Configuration:                                                     │
│  name: customer_features                                                         │
│  entities: [customer_id]                                                         │
│  features:                                                                        │
│    - total_orders (int64)                                                        │
│    - avg_order_value (float64)                                                   │
│  source:                                                                          │
│    type: FileSource                        Advantages:                           │
│    path: s3://bucket/iceberg/gold/         - No data duplication                │
│           customer_features/data/*.parquet  - Always up-to-date                 │
│    timestamp_field: updated_at              - Single source of truth            │
│  ttl: 86400 seconds (24 hours)             - Storage cost savings               │
│                                                                                   │
│  Endpoints:                                                                       │
│  POST /feast/features         - Register feature view from Gold layer           │
│  POST /feast/features/service - Create feature service (grouping)               │
│  GET  /feast/features         - List all feature views                          │
│  GET  /feast/status           - Feature store health check                      │
│                                                                                   │
│  Feature Retrieval (for ML):                                                     │
│  - Historical Features: Query S3 Parquet directly via Feast                     │
│  - Point-in-time joins: Feast handles temporal correctness                      │
│  - Used by MLOps layer for training data preparation                            │
│                                                                                   │
└────────────┬────────────────────────────────────────────────────────────────────┘
             │
             ▼ Features → Model Training → Deployment
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  Layer 5: ML OPERATIONS (MLOps)                 Storage: Models & Artifacts     │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ 5.1: Model Training & Tracking (MLflow)                                  │   │
│  │─────────────────────────────────────────────────────────────────────────│   │
│  │                                                                           │   │
│  │  MLflow Server (Kubernetes Service)                                      │   │
│  │  - PostgreSQL backend for metadata       Model Artifacts:                │   │
│  │  - S3 artifact storage                   s3://bucket/mlflow/artifacts/   │   │
│  │  - Experiment tracking                     ├── {run_id}/                 │   │
│  │  - Model registry                          │   ├── model.pkl            │   │
│  │                                             │   ├── requirements.txt      │   │
│  │  Training Pipeline:                        │   └── MLmodel               │   │
│  │  1. Fetch features from Feast             └── ...                        │   │
│  │  2. Prepare training data                                                │   │
│  │  3. Train model (sklearn/xgboost/etc)     MLflow Metadata:               │   │
│  │  4. Log to MLflow:                        PostgreSQL Database:            │   │
│  │     - Parameters                          - Experiments                   │   │
│  │     - Metrics (accuracy, F1, etc)         - Runs (with params/metrics)   │   │
│  │     - Model artifact                      - Models (registry)             │   │
│  │     - Requirements.txt                    - Model versions                │   │
│  │  5. Register in Model Registry            - Stages (dev/staging/prod)    │   │
│  │                                                                           │   │
│  │  Endpoints:                                                                │   │
│  │  POST /mlops/deploy      - Train model with Feast features             │   │
│  │  GET  /mlops/models        - List models
      GET  /mlops/deployments/{deploymentid}                           │   │
│  │                           │   │
│  │                                                                           │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ 5.2: Asynchronous Model Deployment (Kaniko + K8s)                        │   │
│  │─────────────────────────────────────────────────────────────────────────│   │
│  │                                                                           │   │
│  │  Deployment Flow (Async with Background Threading):                      │   │
│  │                                                                           │   │
│  │  Step 1: Submit Deployment (POST /mlops/deploy)                          │   │
│  │  ────────────────────────────────────────────                            │   │
│  │  Input:                                                                   │   │
│  │    {                                                                      │   │
│  │     "script_name": "train_model.py",
         "script_content": "...",
         "experiment_name": "production_experiment",
         "model_name": "customer_churn_model",
         "requirements": ["scikit-learn", "pandas", "numpy"],
         "environment_vars": {},
         "timeout": 300,
         "tags": {"version": "1.0"},
         "replicas": 2,
         "namespace": "asgard"                                     │   │
│  │    }                                                                      │   │
│  │                                                                           │   │
│  │  Immediate Response:                                                      │   │
│  │    {                                                                      │   │
│  │      "deployment_id": "cd848ae2-f42a-420c-bf98-ae6e32e00974",            │   │
│  │      "model_name": "churn_predictor",                                    │   │
│  │      "status": "submitted",                                              │   │
│  │      "message": "Deployment submitted. Poll /mlops/deployments/{id}"     │   │
│  │    }                                                                      │   │
│  │                                                                           │   │
│  │  Background Thread Starts:                                                │   │
│  │  - Status: "submitted" → "running"                                        │   │
│  │  - Updates deployment tracking dict throughout process                   │   │
│  │                                                                           │   │
│  │  Step 2: Background Execution Pipeline                                    │   │
│  │  ───────────────────────────────────────                                 │   │
│  │                                                                           │   │
│  │  Phase A: Model Training (status: "training")                            │   │
│  │    1. Fetch features from Feast offline store                            │   │
│  │    2. Execute user's training script                                     │   │
│  │    3. Log to MLflow (metrics, params, model)                             │   │
│  │    4. Save model.pkl + requirements.txt                                  │   │
│  │    Duration: ~30-60 seconds                                              │   │
│  │                                                                           │   │
│  │  Phase B: Docker Build (status: "building")                              │   │
│  │    1. Create Dockerfile:                                                 │   │
│  │       FROM python:3.11-slim                                              │   │
│  │       COPY model.pkl /app/                                               │   │
│  │       COPY requirements.txt /app/                                        │   │
│  │       COPY inference_service.py /app/  # FastAPI server                 │   │
│  │       RUN pip install -r requirements.txt                                │   │
│  │       CMD ["uvicorn", "inference_service:app"]                           │   │
│  │                                                                           │   │
│  │    2. Build using Kaniko (in-cluster, no Docker daemon):                │   │
│  │       apiVersion: v1                                                     │   │
│  │       kind: Pod                                                          │   │
│  │       spec:                                                              │   │
│  │         containers:                                                      │   │
│  │         - name: kaniko                                                   │   │
│  │           image: gcr.io/kaniko-project/executor:latest                  │   │
│  │           args:                                                          │   │
│  │           - --context=/workspace                                         │   │
│  │           - --destination=637423.dkr.ecr.eu-north-1.amazonaws.com/      │   │
│  │                           model-{deployment_id}:latest                   │   │
│  │           volumeMounts:                                                  │   │
│  │           - name: workspace                                              │   │
│  │             mountPath: /workspace                                        │   │
│  │           - name: ecr-credentials                                        │   │
│  │             mountPath: /kaniko/.docker                                   │   │
│  │                                                                           │   │
│  │    3. Push to ECR                                                        │   │
│  │    Duration: ~2-3 minutes                                                │   │
│  │                                                                           │   │
│  │  Phase C: Kubernetes Deployment (status: "deploying")                    │   │
│  │    1. Create Deployment:                                                 │   │
│  │       apiVersion: apps/v1                                                │   │
│  │       kind: Deployment                                                   │   │
│  │       metadata:                                                          │   │
│  │         name: model-{deployment_id}                                      │   │
│  │       spec:                                                              │   │
│  │         replicas: 1                                                      │   │
│  │         template:                                                        │   │
│  │           spec:                                                          │   │
│  │             containers:                                                  │   │
│  │             - name: inference                                            │   │
│  │               image: 637423.dkr.ecr../model-{id}:latest                 │   │
│  │               ports:                                                     │   │
│  │               - containerPort: 8000                                      │   │
│  │                                                                           │   │
│  │    2. Create LoadBalancer Service:                                       │   │
│  │       apiVersion: v1                                                     │   │
│  │       kind: Service                                                      │   │
│  │       spec:                                                              │   │
│  │         type: LoadBalancer                                               │   │
│  │         ports:                                                           │   │
│  │         - port: 80                                                       │   │
│  │           targetPort: 8000                                               │   │
│  │                                                                           │   │
│  │    3. Wait for external IP assignment                                    │   │
│  │    Duration: ~30-60 seconds                                              │   │
│  │                                                                           │   │
│  │  Total Deployment Time: ~3.5-5 minutes                                   │   │
│  │                                                                           │   │
│  │  Step 3: Poll Status (GET /mlops/deployments/{deployment_id})            │   │
│  │  ──────────────────────────────────────────────────────────              │   │
│  │                                                                           │   │
│  │  Response (during deployment):                                            │   │
│  │    {                                                                      │   │
│  │      "deployment_id": "cd848ae2-f42a-420c-bf98-ae6e32e00974",            │   │
│  │      "status": "running",                                                │   │
│  │      "progress": "training",  # or "building", "deploying"               │   │
│  │      "submitted_at": "2025-11-14T06:54:50Z",                             │   │
│  │      "started_at": "2025-11-14T06:54:51Z",                               │   │
│  │      "completed_at": null,                                               │   │
│  │      "inference_url": null,  # Available when completed                 │   │
│  │      "error": null                                                       │   │
│  │    }                                                                      │   │
│  │                                                                           │   │
│  │  Response (completed):                                                    │   │
│  │    {                                                                      │   │
│  │      "deployment_id": "cd848ae2-f42a-420c-bf98-ae6e32e00974",            │   │
│  │      "status": "deployed",                                               │   │
│  │      "progress": "completed",                                            │   │
│  │      "inference_url": "http://51.89.229.98",                             │   │
│  │      "external_ip": "51.89.229.98",                                      │   │
│  │      "endpoints": {                                                       │   │
│  │        "health": "http://51.89.229.98/health",                           │   │
│  │        "predict": "http://51.89.229.98/predict",                         │   │
│  │        "docs": "http://51.89.229.98/docs"                                │   │
│  │      },                                                                   │   │
│  │      "run_id": "3b9a6b66ac084a9f8e5c2d1f9a7b4e8c",                       │   │
│  │      "model_version": "1",                                               │   │
│  │      "ecr_image": "637423.dkr.ecr../model-cd848ae2:latest",             │   │
│  │      "completed_at": "2025-11-14T06:58:30Z"                              │   │
│  │    }                                                                      │   │
│  │                                                                           │   │
│  │  Step 4: Use Deployed Model                                               │   │
│  │  ────────────────────────────                                            │   │
│  │                                                                           │   │
│  │  Health Check:                                                            │   │
│  │    curl http://51.89.229.98/health                                       │   │
│  │    → {"status": "healthy", "model": "churn_predictor"}                   │   │
│  │                                                                           │   │
│  │  Make Predictions:                                                        │   │
│  │    curl -X POST http://51.89.229.98/predict \                            │   │
│  │      -H "Content-Type: application/json" \                               │   │
│  │      -d '{"features": [[1.2, 3.4, 5.6]]}'                                │   │
│  │    → {"predictions": [0, 1, 1]}                                           │   │
│  │                                                                           │   │
│  │  Endpoints:                                                                │   │
│  │  POST /mlops/deploy                    - Submit async deployment         │   │
│  │  GET  /mlops/deployments/{id}          - Poll deployment status          │   │
│  │  GET  /mlops/deployments               - List all deployments            │   │
│  │                                                                           │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  Key Design Decisions:                                                           │
│  - Async deployment with immediate response (no waiting 3-5 minutes)             │
│  - Background threading for non-blocking execution                               │
│  - Status polling pattern for progress tracking                                  │
│  - In-memory deployment tracking (dict-based state management)                   │
│  - Kaniko for in-cluster Docker builds (no Docker daemon required)              │
│  - ECR for container registry                                                    │
│  - LoadBalancer service for automatic external IP assignment                    │
│  - Pickle serialization for model persistence                                   │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎥 Video Walkthrough: ERP Production Data Journey

This section tells the story of how real manufacturing data travels through the entire Asgard platform, transforming from raw database records into a production-ready machine learning model. Think of it as following a single batch of data on its complete journey through 5 transformation stages.

### 📊 Our Starting Point: Factory Production Data

Imagine a manufacturing company with a production database that tracks everything happening on the factory floor. This database contains:

**What the Data Represents:**

- Work orders showing which products were made, when, and by whom
- Machine logs recording every piece of equipment activity
- Quality inspection results from the quality control team
- Inventory records of raw materials used

 

**The Data's Initial State:**
This factory data is messy, like most real-world data. It has typos, missing information, inconsistent formatting, and duplicates - basically all the problems you'd expect from data entered by busy factory workers across multiple shifts.

---

### Video 1: Connecting to the Factory Database (52 seconds)

**Watch:** https://www.loom.com/share/9f4a68406c03405dafe0e13f8cdae016

 

This first video shows the very beginning of our data journey. At this point, all the factory data is still sitting in the production database at the manufacturing facility. We haven't moved any data yet - we're just introducing the Asgard platform to that database.

**What You See Happening:**

1. **Opening the API Gateway:** The video starts at the Asgard platform's API documentation page - this is our control panel for all data operations. We navigate to the data ingestion section.

2. **Finding the "Create Data Source" Endpoint:** We locate the `/datasource` endpoint, which is specifically designed to register new external data sources. This is the entry point for connecting any external system (databases, APIs, file systems, etc.) to the Asgard platform.

3. **Configuring the Factory Database Connection:** We fill in the connection details for the manufacturing company's production database:
    - **Source Type:** PostgreSQL (the type of database the factory uses)
    - **Host/Port:** The network address where the factory database lives
    - **Database Name:** The specific database containing production data
    - **Credentials:** Username and password for secure access
  
4. **Airbyte Working Behind the Scenes:** When we submit this request, Airbyte (the data movement engine) receives the configuration and:
    - Tests the connection to verify it can reach the factory database
    - Validates the credentials work correctly
    - Registers this as a "source" that can later be connected to a destination

5. **Success Confirmation:** The platform responds with a source ID (like a registration number) confirming that Asgard now knows about this factory database and can access it when we're ready to copy data.

**Key Point:** At this stage, NO data has moved yet. We've simply introduced Asgard to the factory database - like exchanging business cards. The actual data transfer happens in the next step (Video 2) when we create an "ingestion pipeline" connecting this source to a destination.
 

---

### Video 2: Creating Sink and Ingestion Pipeline -> Copying Data to Cloud Storage (3 minutes)

**Watch:** https://www.loom.com/share/722f8a82192c4c4787413727932d5cdd

#### The Story:

Now that Asgard knows about the factory database, we're going to actually copy the data into cloud storage. This video shows two important steps: first telling Asgard where to put the data, and then starting the actual copy process.

**Part 1: Setting Up the Destination**

Before we can copy data, we need a place to put it. We're using Amazon S3 (cloud storage) as our "Bronze layer" - this is where we'll store an exact copy of the factory data.

Think of S3 like a massive digital warehouse with unlimited shelves. We're telling Asgard:

- Use this specific S3 bucket (our warehouse)
- Put the data in the "bronze/erp_production" folder (our shelf)
- Store it in Parquet format (an efficient file format for data)
- Compress it to save space

The platform confirms "OK, I've set up that destination and I'm ready to receive data there."

**Part 2: Connecting Source to Destination (45 seconds to 1 minute 30 seconds)**

Now comes the crucial step - we're creating a "pipeline" that connects our factory database (the source) to our cloud storage (the destination).

We specify exactly which tables we want to copy:

- production.work_orders (the main production records)
- production.machine_logs (equipment activity)
- production.quality_checks (inspection results)
- inventory.materials (raw materials)

We also decide when to run this copy: manual (just once, for this demonstration) rather than on a schedule or cron.

**Part 3: The Data Transfer Begins**

When we click execute, something amazing happens in the background. Airbyte (the data movement engine) starts:

- Connecting to the factory database
- Reading table by table
- Converting each table to Parquet format
- Uploading to S3 cloud storage

You can see the status change to "syncing" - meaning data is actively flowing from the factory to the cloud.

**Part 4: Checking the Results**

We check the status and see beautiful confirmation:

- Status: "succeeded" ✓
- Total records copied: 45,823
- Breakdown: 15,000 work orders, 25,000 machine logs, 3,500 quality checks, 2,323 inventory items

**Understanding What Just Happened with the Data:**

Imagine photocopying a filing cabinet. The original factory data is still in the production database (the original filing cabinet), completely unchanged and still being used by the factory. But now we also have a complete copy in cloud storage (our photocopy) that we can analyze without disturbing production.

**Critical Point About Data Quality:**

This copied data is still "raw" - it has all the same problems as the original:

- Some work orders say "completed" while others say "COMPLETED" (inconsistent capitalization)
- Some records have missing information (like an operator ID that's blank)
- Product codes are formatted differently (sometimes "PROD-123", sometimes "prod-123")
- There might be incomplete records (work orders that started but have no end time)

We're keeping all these imperfections on purpose! This Bronze layer serves as our "source of truth" - an untouched archive that we can always come back to if we need to reprocess data differently later.

**Data State After Video 2:**

- Location: Now in cloud storage (S3) AND still in the factory database
- Format: Parquet files (efficient columnar storage)
- Volume: 45,823 total records across 4 different types
- Quality: Raw and messy (exact copy of source)
- Organization: Split into separate folders for each data type
- Next Step: Clean up this messy data

---
 ### Video 3: Cleaning and Standardizing the Data (2 minutes 33 seconds)

**Watch:** https://www.loom.com/share/970f5778015c486985e295a095279e02

#### The Story:

Our data is now safely in cloud storage, but it's still messy. This video shows how we use Apache Spark (a powerful data processing engine) to clean, standardize, and validate the data. Think of this as taking rough lumber and planing it smooth - we're keeping the same pieces but making them uniform and ready to use.

**Part 1: Seeing the Raw Data (First 30 seconds)**

The video starts by showing us the actual files in Amazon S3 storage. We can see the Parquet files that were created in Video 2 - these are our raw work orders, machine logs, quality checks, and inventory data sitting in the "bronze" folder.

**Part 2: Writing the Cleaning Instructions**

Now we're telling Spark exactly how to clean the data. Here's what we're asking Spark to do, explained in plain English:

**Standardizing Text:**

- Make all work order IDs and product IDs uppercase and remove extra spaces
- Convert all status values to lowercase for consistency
 
**Fixing Time Information:**

- Ensure all dates and times are stored in proper timestamp format
 
**Adding Quality Flags:**

- Label each record as "VALID" or "INVALID"
- Invalid examples: completed orders with no end time, orders with zero quantity
- This lets us filter later while keeping the problematic records for analysis

**Adding Tracking Information:**

- Stamp each record with when it was processed
- Note which cleaning rules were applied (version tracking)

**Part 3: Running the Spark Job**

When we submit this job, Spark spins up virtual computers in the cloud (called executors) and processes the data in parallel. It's like having multiple workers cleaning different sections of a warehouse simultaneously.

We can watch the progress:

- "SUBMITTED" - Spark accepts the job
- "RUNNING" - Processing is happening
- "COMPLETED" - All 15,000 work orders have been cleaned

The entire cleaning process takes only 45 seconds despite processing thousands of records because Spark distributes the work across multiple computers.

**Part 4: Checking the Results**

We navigate to the "silver" folder in S3 storage and find new Parquet files. These contain our cleaned data. We also see that Spark has registered this cleaned data in the Iceberg catalog (a data lakehouse system) making it easy to query later.

**Understanding the Data Transformation:**

**Before (Bronze Layer) - Example Work Order:**

- Work Order: wo-001 (or WO-001 or Wo-001 - inconsistent)
- Product: PROD-123 (or prod-123 or Prod-123 - inconsistent)
- Status: completed (or COMPLETED or Completed - inconsistent)
- Quantity: blank or negative numbers
- Operator: blank field
- Duration: not calculated

**After (Silver Layer) - Same Work Order:**

- Work Order: WO-001 (always uppercase, trimmed)
- Product: PROD-123 (standardized format)
- Status: completed (always lowercase)
- Quantity: 500 (or 0 if it was invalid)
- Operator: EMP-045 (or UNASSIGNED if it was blank)
- Duration: 8.5 hours (calculated from start and end times)
- Quality Flag: VALID (or INVALID if there are issues)
- Processed: 2025-11-12 at 14:23:45

**What Got Filtered:**
Out of 15,000 original work orders, 150 were so badly damaged (like having no work order ID at all) that they were removed. But we still kept 14,850 good records, including some marked "INVALID" that we might want to investigate later.

**Data State After Video 3:**

- Location: S3 "silver" folder + Iceberg catalog
- Format: Clean, standardized Parquet files
- Volume: 14,850 work orders (150 completely invalid ones removed)
- Quality: Cleaned, typed, validated
- Improvements: Consistent formatting, null handling, calculated fields, quality flags
- Next Step: Create features for machine learning

---

### Video 4: Creating Machine Learning Features

**Watch:** https://www.loom.com/share/c307e1201f454b3ebbc81160926b9049

#### The Story:

Now we have clean data, but it's still just individual work orders. For machine learning, we need to summarize this into meaningful patterns. This video shows how we transform 14,850 individual work order records into 142 operator performance profiles. Think of it as turning individual test scores into student report cards.

**Part 1: Understanding the Goal**

We're trying to answer: "Which operators are high performers?" To do this, we need to look at each operator's entire history and calculate their statistics. Instead of looking at one work order at a time, we're going to group all work orders by operator and calculate meaningful metrics.

**Part 2: Checking What's Available**

We check what tables are in the Silver layer and see our cleaned work orders are ready. The data shows each record has operator ID, duration, quantity produced, status, and quality flags.

**Part 3: The Feature Engineering Process**
Now we're using DBT (Data Build Tool) to create sophisticated calculations. Here's what's happening, explained in simple terms:

**Grouping the Data:**

- Take all 14,850 work orders
- Group them by operator (so all of EMP-045's work orders together, all of EMP-067's together, etc.)
- This gives us about 142 different operators

**Calculating Performance Metrics for Each Operator:**

**Volume Metrics:**

- Count how many work orders they completed (some did 87, some did 105, etc.)
- Count how many succeeded vs failed
- Sum up total units they produced

**Efficiency Metrics:**

- Calculate their average time per work order (some average 8.2 hours, others 9.5 hours)
- Find their fastest and slowest times
- Calculate consistency (do they work at steady pace or vary wildly?)

**The Key Efficiency Score:**

- Units per hour = Total units ÷ Total hours worked
- This is the golden metric: Someone producing 92.5 units/hour is more efficient than someone producing 48.2 units/hour

**Success Rate:**

- Completion rate = Completed orders ÷ Total orders
- Someone with 97.7% completion rate is more reliable than someone with 72.6%

**Creating the Target Variable (What We Want to Predict):**

- Label someone as "high performer" (value: 1) if they meet BOTH criteria:
  - Produce more than 75 units per hour AND
  - Complete more than 90% of their work orders successfully
- Everyone else gets labeled as "needs improvement" (value: 0)

**Quality Control:**

- Only use work orders marked as VALID (ignore the problematic ones)
- Only include operators with at least 5 work orders (otherwise statistics aren't meaningful)

**Part 4: Execution and Results**

DBT submits this transformation to Trino (a query engine) which processes it in about 8.5 seconds. The result:

- Started with: 14,850 individual work order records
- Ended with: 142 operator summary profiles
- Each profile has: 8-9 calculated features plus the target label

The data is saved in the "Gold" layer of our Iceberg data lakehouse.

**Understanding the Transformation with a Real Example:**

**Silver Layer - Individual Records for Operator EMP-045:**

- Work Order 1: 8.2 hours, 500 units, completed
- Work Order 2: 8.5 hours, 550 units, completed
- Work Order 3: 7.8 hours, 480 units, completed
- ... (87 total work orders)

**Gold Layer - Summary Profile for Operator EMP-045:**

- Operator: EMP-045
- Total Work Orders: 87
- Completed Successfully: 85 (97.7% completion rate)
- Total Units Produced: 43,500
- Average Duration: 8.2 hours per order
- Units Per Hour: 92.5 (very efficient!)
- Products Handled: 12 different types
- Data Quality Score: 98% of their records were clean
- Label: HIGH PERFORMER (1) ✓

**Why This Matters:**

We've transformed the question from "What happened in work order WO-001?" to "Is operator EMP-045 a high performer?" The first question needs thousands of rows to answer. The second question is now just one row with all the relevant statistics pre-calculated.

**Data State After Video 4:**

- Location: Iceberg Gold layer
- Format: Operator summary table (one row per operator)
- Volume: 142 operator profiles (from 14,850 work orders)
- Content: Performance metrics, efficiency scores, target labels
- Quality: ML-ready (no further calculations needed)
- Next Step: Register these features for reuse

---

### Video 5: Registering Features for Machine Learning (1 minute 8 seconds)

**Watch:** https://www.loom.com/share/d13de4c4c8604ac19091605a2cd3af3e

#### The Story:

We now have beautiful, clean, calculated features in our Gold layer. But here's a problem: if different data scientists want to use these features, how do they know they exist? How do they know what each feature means? This is where Feast (the feature store) comes in. Think of it like creating a catalog or menu of available features.

**Part 1: Understanding the Problem (First 25 seconds)**

Imagine a company library. You have great books (our features), but if there's no card catalog, nobody knows what books are available or where to find them. Feast is that card catalog for our features.

**Part 2: Registering the Features (25 seconds to 50 seconds)**

We're now telling Feast about our operator efficiency features. Here's what we're documenting:

**The Entity:**

- This feature set is organized by "operator_id"
- Meaning: each row represents one operator
- Think of this as the "index" or "key" for looking up features

**The Features (What's Available):**
We list out each calculated metric and describe what it means:

- "total_work_orders" - How many assignments they've completed
- "completed_orders" - How many they successfully finished
- "avg_duration_hours" - Their average speed
- "units_per_hour" - Their efficiency score
- "completion_rate" - Their success percentage
- "is_high_performer" - The label we want to predict

**Where the Data Lives:**

- Source table: "production_operator_features" in the Gold layer
- Storage location: S3 Parquet files in Iceberg
- Timestamp field: "feature_timestamp" (for point-in-time lookups)

**Important Decision - No Data Copying:**

- Feast does NOT copy the data from Gold layer
- It just records: "If you need operator features, read from this S3 path"
- This saves storage space and ensures features are always up-to-date

**Part 3: What Happens Behind the Scenes (50 seconds to 1 minute 8 seconds)**

When we click execute, Feast:

**Step 1: Validates Everything Exists**

- Connects to Trino query engine
- Runs a test query: "Can I access iceberg.gold.production_operator_features?"
- Confirms the table exists and has the expected columns

**Step 2: Gets the Physical Location**

- Asks Iceberg: "Where is this table actually stored?"
- Iceberg responds: "s3://airbytedestination1/iceberg/gold/production_operator_features/data/\*.parquet"
- Feast records this path

**Step 3: Registers Metadata**

- Creates an "Entity" definition for operator_id
- Creates a "Feature View" listing all 9 features
- Stores this catalog information in a tiny database (SQLite registry)
- Total storage used: A few kilobytes (just metadata, not actual data)

**Step 4: Confirms Success**

- Returns a message: "Feature view 'operator_efficiency_features_v1' successfully registered"
- Features are now discoverable and reusable

**Understanding the Architecture:**

**What's Stored Where:**

**Feast Registry (tiny database):**

- Catalog Entry:
  - Feature View Name: operator_efficiency_features_v1
  - Entity: operator_id
  - Features: [list of 9 feature names with descriptions]
  - Data Location: s3://bucket/iceberg/gold/.../data/\*.parquet
  - Schema: [data types for each feature]
  - Freshness: Updated when feature_timestamp changes

**Actual Data (S3 Parquet files):**

- s3://airbytedestination1/iceberg/gold/production_operator_features/data/
  - Contains the actual 142 operator profiles
  - No duplication - same files Trino uses for queries
  - Feast reads directly from here when features are requested

**How Machine Learning Will Use This:**

Later, when we train a model, here's what happens:

1. ML code asks Feast: "Give me features for operators EMP-045, EMP-067, EMP-112"
2. Feast checks its registry: "OK, those are in operator_efficiency_features_v1"
3. Feast looks up the S3 path from its registry
4. Feast reads the Parquet files directly from S3
5. Feast returns only the requested operators' features
6. ML model receives a clean table ready for training

**The Brilliant Part - Zero Duplication:**

The same Parquet files serve three purposes:

- Trino can query them for analytics ("Show me average efficiency by shift")
- Feast serves them for ML training ("Give me features for model training")
- Data engineers can read them directly for investigations

There's only ONE copy of the data, but THREE different tools can use it. This saves storage costs and ensures everyone is working with the same, up-to-date information.

**Data State After Video 5:**

- Location: Still in Iceberg Gold layer (unchanged)
- Catalog: Now registered in Feast feature store
- Accessibility: Easily discoverable and reusable
- Storage: No duplication (Feast stores only metadata)
- Next Step: Use these features to train a model

---

### Video 6: Training and Deploying the Model (2 minutes 31 seconds)

**Watch:** https://www.loom.com/share/bf5db222aca24270970807239ac1cc98

#### The Story:

This is the grand finale - where all our data preparation pays off. We're going to train a machine learning model to predict operator performance and deploy it as a real, working web service that anyone can call for predictions. This entire process happens automatically in the background.

**Part 1: Understanding the Async Workflow**

Unlike the previous steps, this one takes several minutes (building Docker images, training models, etc.). So the platform works differently:

- We submit a request
- We get back an ID immediately
- The work happens in the background
- We check status periodically until it's done

Think of it like ordering food delivery: you place the order (get a tracking number), the restaurant cooks your food (background work), and you check the status occasionally until it arrives.

**Part 2: Submitting the Deployment Request**

We're telling the MLOps system several things:

**Model Configuration:**

- Name: "operator_efficiency_predictor"
- Purpose: Predict if an operator is a high performer
- Framework: scikit-learn (a popular Python ML library)

**Data Source:**

- Use the "operator_efficiency_features_v1" from Feast
- Target variable: "is_high_performer" (0 or 1)
- Features: The 8 metrics we calculated (units_per_hour, completion_rate, etc.)

**Training Instructions:**
We provide a script that tells the system how to train the model:

- Split the 142 operators into training set (80%) and test set (20%)
- Use 113 operators to learn patterns
- Reserve 29 operators to validate accuracy
- Train a Random Forest model (an ensemble of decision trees)
- Calculate accuracy, precision, recall, and F1 score

**Part 3: Immediate Response - The Deployment ID (1 minute 10 seconds to 1 minute 20 seconds)**

The system responds instantly:

- Deployment ID: "f8c3d9e1-7b2a-4f5c-9a1e-6d4c8b3f7a2e"
- Status: "submitted"
- Message: "Check this ID periodically for progress"

At this point, a background thread starts working on our request while we're free to do other things.

**Part 4: Polling for Progress (1 minute 20 seconds to 2 minutes)**

We check the deployment ID status every 10 seconds and watch it progress through three stages:

**Stage 1: Training (First 30-45 seconds)**
Status shows: "progress: training"

**What's Happening in the Background:**

- Feast connects to S3 and reads the 142 operator profiles
- The data is split: 113 for training, 29 for testing
- A Random Forest model is trained (like building 100 decision trees that vote on predictions)
- The model learns patterns: "If units_per_hour > 75 AND completion_rate > 0.90, probably a high performer"
- Model is tested on the 29 reserved operators
- Results: 93.1% accuracy! Out of 29 test cases, we got 27 correct
- Model is saved as a file (model.pkl)
- Everything is logged to MLflow (experiment tracking system)

**Stage 2: Building (Next 1.5-2 minutes)**
Status shows: "progress: building"

**What's Happening in the Background:**

- A Docker container is being created (a self-contained package with everything needed to run the model)
- The container includes:
  - Python programming language
  - The trained model file (model.pkl)
  - A web server to accept prediction requests
  - All necessary libraries
- This container is built using Kaniko (builds Docker images inside Kubernetes)
- Once built, it's uploaded to Amazon ECR (container registry)
- Image name: "model-f8c3d9e1:latest"

Think of this like packaging a complete meal kit: instead of sending someone just the recipe (the model), we're sending them a box with all ingredients, cooking tools, and instructions ready to go.

**Stage 3: Deploying (Final 30-60 seconds)**
Status shows: "progress: deploying"

**What's Happening in the Background:**

- Kubernetes creates a new "Deployment" (instructions to run our container)
- A pod (virtual server) starts up running our container
- A "LoadBalancer" service is created (gives us a public web address)
- The cloud provider assigns an external IP address
- Health checks confirm the service is responding
- Final IP: 51.89.227.145

**Part 5: Deployment Complete (2 minutes to 2 minutes 20 seconds)**

The final status check shows:

- Status: "deployed" ✓
- Inference URL: http://51.89.227.145
- Endpoints available:
  - Health check: /health (is the service running?)
  - Predictions: /predict (make predictions)
  - Documentation: /docs (interactive API docs)
- Total time: About 3 minutes 15 seconds from submission to live service

**Part 6: Using the Deployed Model (2 minutes 20 seconds to 2 minutes 31 seconds)**

Now we test the live service:

**Health Check:**
We call: http://51.89.227.145/health
Response: "status: healthy, model: operator_efficiency_predictor"
This confirms the service is running and ready.

**Making Real Predictions:**

We send three operators' data to the prediction API:

**Operator 1 Data:**

- 87 work orders completed
- 85 successful
- 43,500 units produced
- 8.2 hours average
- 92.5 units per hour ← High efficiency!
- 97.7% completion rate ← Very reliable!
  **Prediction: 1 (High Performer!) ✓**
  **Confidence: 88% sure**

**Operator 2 Data:**

- 62 work orders
- 45 successful
- 18,750 units produced
- 9.5 hours average
- 48.2 units per hour ← Below threshold
- 72.6% completion rate ← Below threshold
  **Prediction: 0 (Needs Improvement)**
  **Confidence: 73% sure**

**Operator 3 Data:**

- 105 work orders
- 98 successful
- 52,500 units produced
- 7.8 hours average
- 95.3 units per hour ← Excellent!
- 93.3% completion rate ← Very good!
  **Prediction: 1 (High Performer!) ✓**
  **Confidence: 92% sure**

**Understanding What We've Achieved:**

**The Complete Journey:**

1. Started with: Raw factory database with 15,000 messy work order records
2. Copied to: Cloud storage (Bronze layer)
3. Cleaned to: Standardized records (Silver layer) - 14,850 records
4. Summarized to: Operator profiles (Gold layer) - 142 profiles
5. Cataloged in: Feature store (Feast) for reusability
6. Trained: Machine learning model with 93.1% accuracy
7. Deployed: Live web service at http://51.89.227.145

**Business Value:**

- **Speed:** Model responds in under 50 milliseconds
- **Accuracy:** Correctly identifies 27 out of 29 operators (93.1%)
- **Availability:** Anyone can call this web service 24/7
- **Scalability:** Can handle thousands of prediction requests per second
- **Use Cases:**
  - HR can identify operators for bonuses
  - Managers can assign complex jobs to high performers
  - Training teams can identify who needs help
  - Scheduling software can optimize shift assignments

**The Model's "Brain":**

The model learned that the two most important factors are:

1. **Units per hour** (34.2% importance) - Direct productivity measure
2. **Completion rate** (28.7% importance) - Reliability measure

It discovered patterns like: "If someone produces > 75 units/hour AND completes > 90% of jobs, they're almost certainly a high performer."

**Data State After Video 6:**

- Location: Running as a live service in Kubernetes
- Access: Public URL at http://51.89.227.145
- Response Time: < 50ms per prediction
- Model Performance: 93.1% accurate on test data
- Deployment: Fully automated from training to production
- Status: Ready for real-world use
