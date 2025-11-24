# Asgard Data Platform

**Modern Data Lakehouse + MLOps Platform**  
_End-to-end data pipeline: Airbyte → Spark → DBT → Feast → MLOps_

[![Production Ready](https://img.shields.io/badge/status-production%20ready-green)]()
[![Kubernetes](https://img.shields.io/badge/kubernetes-native-blue)]()
[![API](https://img.shields.io/badge/API-FastAPI-teal)]()

---

## 🎯 What is Asgard?

A **unified data platform** that orchestrates the complete data lifecycle from raw data ingestion to ML model deployment through a **single REST API**.

```
External DBs → Airbyte → Spark → DBT → Feast → MLOps
    ↓           ↓         ↓       ↓      ↓       ↓
 Sources     Bronze    Silver   Gold  Features Models
```

### Key Features

✅ **Single API Surface** - All operations through one FastAPI endpoint  
✅ **Zero Data Duplication** - Feast reads directly from Iceberg S3 Parquet  
✅ **Medallion Architecture** - Bronze → Silver → Gold data layers  
✅ **ML-Ready Features** - Seamless feature engineering to model training  
✅ **Kubernetes Native** - Scalable, production-ready, auto-scaling  
✅ **Open Source** - Built on proven open-source tools

---

## 📚 Documentation

### 🌟 **Start Here** (New Users)

| Document                                                | Description                           | Time    |
| ------------------------------------------------------- | ------------------------------------- | ------- |
| **[� Onboarding & Setup](./docs/ONBOARDING_SETUP.md)**  | Complete setup and installation guide | 30 min  |
| **[📖 End-to-End Use Case](./docs/USE_CASE_GUIDE.md)**  | Customer churn prediction workflow    | 2-3 hrs |
| **[🧪 API Testing Guide](./docs/API_TESTING_GUIDE.md)** | API reference with testing examples   | 1 hr    |
| **[🎨 Visual Diagrams](./docs/DIAGRAMS.md)**            | System architecture and data flow     | 30 min  |

### 📖 **Complete Documentation**

- **[📘 Documentation Index](./docs/README.md)** - Complete navigation guide
- **[🏗️ Architecture Guide](./docs/ARCHITECTURE.md)** - Technical architecture deep dive
- **[🔧 Debugging Guide](./docs/DEBUGGING_GUIDE.md)** - Troubleshooting and error resolution
- **[🎯 Feast Documentation](./docs/FEAST_API_DEMO_GUIDE.md)** - Feature store guide
- **[🤖 MLOps Guide](./docs/MLOPS_API_DEMO_GUIDE.md)** - Model training and inference

### 🏗️ **Technical Deep Dive**

- **[Complete Architecture](./docs/COMPLETE_ARCHITECTURE.md)** - System architecture with Mermaid diagrams
- **[Feast + Iceberg Architecture](./docs/FEAST_ICEBERG_ARCHITECTURE.md)** - Zero-duplication feature store
- **[Feast UI Setup](./docs/feast-ui/README.md)** - Feature store visualization

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Kubernetes cluster access
- kubectl configured
- S3-compatible storage (AWS S3 or MinIO)

### 5-Minute Setup

```bash
# 1. Port forward Asgard API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# 2. Port forward MLflow UI (optional)
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# 3. Check platform status
curl http://localhost:8000/mlops/status

# 4. Access interactive API docs
open http://localhost:8000/docs
```

### Access Points

- **Asgard API:** http://localhost:8000/docs (Swagger UI)
- **MLflow UI:** http://localhost:5000 (Experiment tracking)

---

## 🎓 Learning Paths

### Path 1: Quick Start (30 minutes)

```
Quick Reference Guide → Try one API call → Read Use Case Phase 1
```

### Path 2: Complete Understanding (2 hours)

```
Quick Reference → Architecture Diagrams → End-to-End Use Case
→ Feast Demo → MLOps Demo
```

### Path 3: Deep Technical Dive (4 hours)

```
All documentation in order (see docs/README.md)
```

---

## 🚀 Real-World Example

### Customer Churn Prediction (30 minutes)

**Step 1:** Ingest customer data from PostgreSQL

```bash
POST /datasource
{
  "source_type": "postgres",
  "name": "customer_db",
  "source_config": {"host": "db.example.com", ...}
}
```

**Step 2:** Clean data with Spark

```bash
POST /spark/transform
{
  "sql_query": "SELECT * FROM bronze.customers WHERE email IS NOT NULL",
  "output_table": "iceberg.silver.customers_cleaned"
}
```

**Step 3:** Create business metrics with DBT

```bash
POST /dbt/transform
{
  "sql_query": "SELECT customer_id, COUNT(*) as orders FROM silver.transactions GROUP BY 1",
  "output_table": "iceberg.gold.customer_metrics"
}
```

**Step 4:** Register features in Feast

```bash
POST /feast/features
{
  "name": "customer_features",
  "source": {"table_name": "customer_metrics", "schema": "gold"}
}
```

**Step 5:** Train ML model

```bash
POST /mlops/training/upload
{
  "script_content": "<base64_python_script>",
  "model_name": "churn_predictor"
}
```

**Step 6:** Get predictions

```bash
POST /mlops/inference
{
  "model_name": "churn_predictor",
  "inputs": {"total_purchases": [5, 25], "lifetime_value": [250, 2500]}
}
```

**Complete example:** See [END_TO_END_USE_CASE.md](./docs/END_TO_END_USE_CASE.md)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│      ASGARD REST API (FastAPI)                  │
│         http://localhost:8000                   │
└──────┬──────────┬──────────┬──────────┬─────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
   Airbyte     Spark      DBT      Feast/MLflow
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────────────────────────────────────────────┐
│    ICEBERG DATA LAKEHOUSE (S3 + Nessie)          │
│  Bronze → Silver → Gold → Features → Models      │
└──────────────────────────────────────────────────┘
```

### Platform Components

| Component      | Purpose               | Technology               |
| -------------- | --------------------- | ------------------------ |
| **Asgard API** | Unified REST endpoint | FastAPI, Python 3.11     |
| **Airbyte**    | Data ingestion        | Airbyte OSS              |
| **Spark**      | Data transformation   | Kubernetes SparkOperator |
| **DBT**        | Business logic        | dbt + Trino              |
| **Feast**      | Feature store         | Feast + Iceberg          |
| **MLOps**      | ML lifecycle          | MLflow 2.16              |
| **Iceberg**    | Data lakehouse        | Apache Iceberg + S3      |
| **Nessie**     | Data catalog          | Project Nessie           |

**Visual diagrams:** [ARCHITECTURE_DIAGRAM.md](./docs/ARCHITECTURE_DIAGRAM.md)

---

## 📊 The Complete Pipeline

### Data Layers (Medallion Architecture)

1. **Bronze** (Raw) - Airbyte ingestion from external sources
2. **Silver** (Cleaned) - Spark data quality and validation
3. **Gold** (Aggregated) - DBT business logic and metrics
4. **Features** (ML-Ready) - Feast feature views
5. **Models** (Deployed) - MLflow trained models

### Workflow Timeline

| Phase                | Duration  | API Calls | Output         |
| -------------------- | --------- | --------- | -------------- |
| Data Ingestion       | 10-30 min | 3-4       | Bronze tables  |
| Spark Transform      | 5-15 min  | 2-3       | Silver tables  |
| DBT Aggregation      | 2-10 min  | 1-2       | Gold tables    |
| Feature Registration | <1 min    | 1-2       | Feast features |
| Model Training       | 5-20 min  | 2         | Trained model  |
| Inference            | <1 sec    | 1         | Predictions    |

**Total first run:** ~30-75 minutes  
**Incremental runs:** ~10-20 minutes

---

## 💡 Why Asgard?

### vs Traditional Approach

| Aspect                 | Traditional     | Asgard           |
| ---------------------- | --------------- | ---------------- |
| **Integration**        | Manual coding   | Single REST API  |
| **Learning Curve**     | Weeks           | Days             |
| **Data Duplication**   | Multiple copies | Zero duplication |
| **Time to Production** | Months          | Weeks            |
| **Scalability**        | Manual tuning   | Auto-scaling     |

### Key Benefits

**For Data Engineers:**

- No complex integrations
- Medallion architecture built-in
- Monitor everything from one dashboard

**For Data Scientists:**

- Features automatically available
- Upload Python script → model trained
- No data engineering required

**For ML Engineers:**

- One-line inference API
- Model versioning built-in
- Production-ready deployment

**For Business:**

- Fast time-to-value (days not months)
- Reduced costs (no duplication)
- Better predictions (quality pipeline)

---

## 🛠️ Installation & Deployment

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd asgard-dev

# Install dependencies
uv sync

# Start the API server
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Kubernetes Deployment

```bash
# Port forward to access services
kubectl port-forward -n asgard svc/asgard-app 8000:80
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
```

### Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000
- **Health Check**: http://localhost:8000/health

## 📖 API Reference

### Quick API Examples

**Data Ingestion** (Airbyte):

```bash
# Create data source
POST /datasource
{"source_type": "postgres", "name": "My DB", ...}

# Start ingestion
POST /ingestion
{"source_id": "...", "destination_id": "...", ...}
```

**Data Transformation** (Spark):

```bash
# Submit transformation
POST /spark/transform
{"sql": "SELECT * FROM source_data WHERE ...", ...}

# Check status
GET /spark/transform/{run_id}/status
```

**Feature Store** (Feast):

```bash
# Register features
POST /feast/features
{"name": "customer_features", "entities": ["customer_id"], ...}

# Get features
GET /feast/features/{name}
```

**ML Training** (MLflow):

```bash
# Upload training script
POST /mlops/training/upload
{"script_content": "<base64>", "model_name": "...", ...}

# Get predictions
POST /mlops/inference
{"model_name": "...", "inputs": {...}}
```

**Interactive Documentation**: http://localhost:8000/docs

## 🏛️ Architecture Overview

### Component Structure

```
app/
├── main.py                      # FastAPI application
├── config.py                    # Configuration
├── airbyte/                     # Data ingestion
├── data_transformation/         # Spark transformations
├── dbt_transformations/         # SQL transformations
├── feast/                       # Feature store
├── mlops/                       # ML lifecycle
└── data_products/               # Data access
```

### Medallion Architecture

**Bronze Layer** → Raw data from sources (Airbyte)  
**Silver Layer** → Cleaned, validated data (Spark)  
**Gold Layer** → Business metrics, ML-ready (DBT)  
**Features** → Feature views for ML (Feast)  
**Models** → Trained models (MLflow)

## 🔧 Configuration

### Key Environment Variables

| Variable           | Description               | Default |
| ------------------ | ------------------------- | ------- |
| `AIRBYTE_BASE_URL` | Airbyte API URL           | -       |
| `SPARK_IMAGE`      | Custom Spark Docker image | -       |
| `S3_SECRET_NAME`   | K8s secret for S3 access  | -       |

See [ONBOARDING_SETUP.md](./docs/ONBOARDING_SETUP.md) for complete configuration guide.

## 📁 Project Structure

```
asgard-dev/
├── app/                         # Platform code
│   ├── airbyte/                # Data ingestion
│   ├── data_transformation/    # Spark jobs
│   ├── dbt_transformations/    # SQL transforms
│   ├── feast/                  # Feature store
│   ├── mlops/                  # ML lifecycle
│   └── main.py                 # FastAPI app
├── docs/                        # Documentation
│   ├── COMPLETE_ARCHITECTURE.md
│   ├── USE_CASE_GUIDE.md
│   └── feast-ui/               # Feast UI setup
├── k8s/                         # Kubernetes manifests
├── helmchart/                   # Helm charts
└── ml_deployment/               # ML deployment scripts
```

## 🤝 Contributing

See documentation in `docs/` folder for contribution guidelines.

## 📄 License

[Add your license information here]
