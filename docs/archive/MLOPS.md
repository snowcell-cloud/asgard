# Asgard MLOps Platform - Complete Guide

**Version**: 3.0.0  
**Last Updated**: October 17, 2025  
**Status**: Production Ready (Batch Predictions Only)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Model Monitoring](#model-monitoring)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Implementation Details](#implementation-details)

---

## 🎯 Overview

The Asgard MLOps platform provides end-to-end ML lifecycle management, integrating **Feast Feature Store** with **MLflow** for production-grade machine learning operations.

### Key Features

✅ **Feature Engineering** - Feast feature store with Iceberg integration  
✅ **Model Training** - MLflow experiment tracking (sklearn, xgboost, lightgbm)  
✅ **Model Registry** - MLflow model versioning  
✅ **Batch Predictions** - Large-scale batch scoring with S3 output  
✅ **Model Monitoring** - Drift detection, data quality, performance tracking  
⚠️ **Real-time Predictions** - Currently disabled (batch only)

### What's New

**October 17, 2025 Updates:**

- ✅ Removed model stage management - use versions directly
- ✅ Added `/mlops/monitoring` endpoint for model monitoring
- ✅ Commented out real-time predictions (batch only)
- ✅ Consolidated all MLOps documentation
- ✅ Cleaned up duplicate APIs between Feast and MLOps

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Asgard ML Pipeline                          │
└─────────────────────────────────────────────────────────┘
         │
         ├─ Data Ingestion      → /airbyte
         ├─ Transformation      → /dbt (Bronze → Silver → Gold)
         ├─ Feature Engineering → /feast/features
         ├─ Model Training      → /mlops/models
         ├─ Model Registry      → /mlops/registry
         ├─ Batch Predictions   → /mlops/serve/batch
         └─ Model Monitoring    → /mlops/monitoring
```

### Component Integration

```
Iceberg/S3 (Gold Layer)
        ↓
┌──────────────────────┐
│  FEAST               │  ← Feature Management
│  /feast/features     │
└──────────────────────┘
        ↓ (features)
┌──────────────────────┐
│  MLOPS               │  ← ML Training & Serving
│  /mlops/models       │
│  /mlops/registry     │
│  /mlops/serve/batch  │
│  /mlops/monitoring   │
└──────────────────────┘
        ↓
Batch Predictions (S3 Parquet)
```

---

## 🚀 Quick Start

### Prerequisites

- MLflow deployed on Kubernetes (see `/mlflow` directory)
- Feast feature store configured
- Python 3.10+
- Access to Iceberg gold layer tables

### Installation

```bash
# 1. Install dependencies
pip install mlflow==2.16.2 lightgbm==4.5.0 scikit-learn xgboost

# 2. Set environment variables
export MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
export FEAST_REPO_PATH=/tmp/feast_repo
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1

# 3. Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5-Step Workflow

#### Step 1: Register Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_features",
    "entities": ["customer_id"],
    "features": [
      {"name": "total_orders", "dtype": "int64"},
      {"name": "avg_order_value", "dtype": "float64"},
      {"name": "days_since_last_order", "dtype": "int64"}
    ],
    "source": {
      "table_name": "customer_aggregates",
      "timestamp_field": "event_timestamp"
    }
  }'
```

#### Step 2: Train Model

```bash
curl -X POST http://localhost:8000/mlops/models \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_name": "customer_churn",
    "model_name": "churn_predictor",
    "framework": "sklearn",
    "model_type": "classification",
    "data_source": {
      "feature_views": ["customer_features"],
      "entities": {"customer_id": [1, 2, 3, 4, 5]},
      "target_column": "churned"
    },
    "hyperparameters": {
      "params": {
        "n_estimators": 100,
        "max_depth": 10,
        "random_state": 42
      }
    }
  }'
```

#### Step 3: Register Model

```bash
curl -X POST http://localhost:8000/mlops/registry \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "churn_predictor",
    "run_id": "<run_id_from_step_2>",
    "description": "Churn prediction model v1"
  }'
```

#### Step 4: Make Batch Predictions

```bash
curl -X POST http://localhost:8000/mlops/serve/batch \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "churn_predictor",
    "model_version": "1",
    "feature_views": ["customer_features"],
    "entities_df": {
      "customer_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    },
    "output_path": "s3://my-bucket/predictions/batch_2025_10_17.parquet"
  }'
```

---

## 📡 API Reference

### Model Training (`/mlops/models`)

#### POST `/mlops/models` - Train Model

Train a new ML model using Feast features.

**Request:**

```json
{
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "framework": "sklearn",
  "model_type": "classification",
  "data_source": {
    "feature_views": ["customer_features"],
    "entities": { "customer_id": [1, 2, 3] },
    "target_column": "churned"
  },
  "hyperparameters": {
    "params": { "n_estimators": 100, "max_depth": 10 }
  },
  "tags": { "team": "data-science" }
}
```

**Response:**

```json
{
  "run_id": "abc123def456",
  "experiment_id": "1",
  "model_name": "churn_predictor",
  "model_uri": "runs:/abc123def456/model",
  "metrics": {
    "metrics": { "train_accuracy": 0.89 }
  },
  "artifact_uri": "s3://mlflow-artifacts/1/abc123def456/artifacts",
  "status": "completed"
}
```

**Supported Frameworks:**

- `sklearn` - Scikit-learn (Random Forest, etc.)
- `xgboost` - XGBoost
- `lightgbm` - LightGBM

#### GET `/mlops/models` - List Models

List all registered models.

#### GET `/mlops/models/{model_name}` - Get Model Details

Get detailed information about a specific model.

---

### Model Registry (`/mlops/registry`)

#### POST `/mlops/registry` - Register Model

Register a trained model to MLflow Model Registry.

**Request:**

```json
{
  "model_name": "churn_predictor",
  "run_id": "abc123def456",
  "description": "Q4 2025 model",
  "tags": { "validated": "true" }
}
```

**Response:**

```json
{
  "model_name": "churn_predictor",
  "version": "1",
  "run_id": "abc123def456",
  "status": "registered"
}
```

---

### Batch Predictions (`/mlops/serve/batch`)

#### POST `/mlops/serve/batch` - Batch Predictions

**Note**: Real-time predictions (`/mlops/serve`) are currently disabled.

Make batch predictions on large datasets.

**Request:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "feature_views": ["customer_features"],
  "entities_df": {
    "customer_id": [1, 2, 3, ..., 10000]
  },
  "output_path": "s3://my-bucket/predictions/batch.parquet"
}
```

**Response:**

```json
{
  "job_id": "batch-abc123",
  "model_name": "churn_predictor",
  "model_version": "1",
  "status": "completed",
  "output_path": "s3://my-bucket/predictions/batch.parquet"
}
```

---

## 📊 Model Monitoring

### POST `/mlops/monitoring` - Log Monitoring Metrics

Log monitoring metrics for deployed models.

**Metric Types:**

- `prediction_drift` - Changes in prediction distribution
- `feature_drift` - Changes in feature distribution
- `data_quality` - Data quality issues (missing values, outliers)
- `model_performance` - Model performance degradation
- `custom` - Custom metrics

**Request:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "metric_type": "prediction_drift",
  "metrics": {
    "drift_score": 0.15,
    "psi": 0.08,
    "js_divergence": 0.12
  },
  "reference_data": {
    "mean": 0.35,
    "std": 0.12
  },
  "current_data": {
    "mean": 0.42,
    "std": 0.15
  },
  "tags": {
    "deployment": "production"
  }
}
```

**Response:**

```json
{
  "monitoring_id": "mon-xyz789",
  "model_name": "churn_predictor",
  "model_version": "1",
  "metric_type": "prediction_drift",
  "metrics": { "drift_score": 0.15 },
  "alert_triggered": true,
  "alerts": ["drift_score drift detected: 0.150"],
  "timestamp": "2025-10-17T10:00:00Z"
}
```

**Alert Thresholds:**

- Drift metrics > 0.1 (10%)
- Missing data > 0.05 (5%)
- Accuracy < 0.7 (70%)

### POST `/mlops/monitoring/history` - Get Monitoring History

Retrieve monitoring history for a model.

**Request:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "metric_type": "prediction_drift",
  "start_date": "2025-10-01T00:00:00Z",
  "end_date": "2025-10-17T23:59:59Z",
  "limit": 100
}
```

**Response:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "total_records": 250,
  "records": [...],
  "summary": {
    "total_alerts": 15,
    "metric_types": ["prediction_drift", "data_quality"],
    "date_range": {
      "start": "2025-10-01T00:00:00Z",
      "end": "2025-10-17T23:59:59Z"
    }
  }
}
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
MLFLOW_ARTIFACT_LOCATION=s3://mlflow-artifacts

# Feast Configuration
FEAST_REPO_PATH=/tmp/feast_repo

# AWS/S3 Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=mlflow-artifacts

# Trino/Iceberg Configuration
TRINO_HOST=trino.data-platform.svc.cluster.local
TRINO_PORT=8080
TRINO_CATALOG=iceberg
GOLD_SCHEMA=gold
```

### MLflow Deployment

See `/mlflow` directory for complete MLflow deployment on Kubernetes.

```bash
cd mlflow
./deploy.sh
```

---

## 🔧 Troubleshooting

### MLflow Connection Issues

```bash
# Check MLflow service
kubectl get svc -n asgard mlflow-service

# Test connection
curl http://mlflow-service.asgard.svc.cluster.local:5000/health

# Port forward if needed
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
```

### Feast Feature Issues

```bash
# List features
curl http://localhost:8000/feast/features

# Check Feast status
curl http://localhost:8000/feast/status
```

### Model Training Fails

**Common Issues:**

1. **Feast features not found** - Ensure features are registered
2. **Insufficient training data** - Check entity values
3. **MLflow connection error** - Verify MLflow is running
4. **S3 permissions** - Check AWS credentials

### Batch Predictions Fail

**Common Issues:**

1. **Model not found** - Check model is registered and in correct stage
2. **Feature mismatch** - Ensure feature views match training
3. **S3 write permissions** - Verify output path is writable

---

## 📝 Implementation Details

### File Structure

```
app/mlops/
├── __init__.py           # Module initialization
├── schemas.py            # 50+ Pydantic models
├── service.py            # MLOpsService (600+ lines)
└── router.py             # 11 FastAPI endpoints

docs/
└── MLOPS.md              # This file (consolidated docs)
```

### Key Components

1. **MLOpsService** (`service.py`)

   - Model training with Feast feature integration
   - MLflow experiment tracking
   - Model registry management
   - Batch prediction execution
   - Monitoring metrics storage

2. **Router** (`router.py`)

   - 11 API endpoints
   - Real-time predictions commented out
   - Comprehensive request/response examples

3. **Schemas** (`schemas.py`)
   - 50+ Pydantic models
   - Full validation and type safety
   - Monitoring metric types

### Monitoring Architecture

```
Model Deployment
      ↓
Prediction Service
      ↓
Log Metrics → /mlops/monitoring
      ↓
In-Memory Storage + MLflow Tracking
      ↓
Alert System (threshold-based)
      ↓
Query History → /mlops/monitoring/history
```

**Monitoring Storage:**

- Primary: In-memory dictionary (fast access)
- Secondary: MLflow tracking (persistent storage)
- Future: Can be extended to PostgreSQL/TimeSeries DB

### Alert System

**Automatic alerts triggered for:**

- Drift > 10%
- Missing data > 5%
- Accuracy < 70%

Alerts are logged to MLflow and returned in API response.

---

## 📚 Additional Resources

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Related Documentation

- Feast Features: `/feast` endpoints
- MLflow Deployment: `/mlflow/README.md`
- API Cleanup: `/API_CLEANUP.md`

### Example Code

Complete examples available in:

- Quick Start section above
- API Reference section
- Swagger UI interactive docs

---

## ✅ Status Summary

| Feature               | Status      | Notes                       |
| --------------------- | ----------- | --------------------------- |
| Model Training        | ✅ Enabled  | sklearn, xgboost, lightgbm  |
| Model Registry        | ✅ Enabled  | Version management          |
| Batch Predictions     | ✅ Enabled  | S3 Parquet output           |
| Real-time Predictions | ⚠️ Disabled | Commented out               |
| Model Monitoring      | ✅ Enabled  | Drift, quality, performance |
| MLflow Integration    | ✅ Enabled  | Full tracking & registry    |
| Feast Integration     | ✅ Enabled  | Feature retrieval           |

---

## 🎉 Summary

The Asgard MLOps platform provides a production-ready ML lifecycle management system with:

- ✅ Clean API architecture (no duplication)
- ✅ MLflow experiment tracking and model registry
- ✅ Feast feature store integration
- ✅ Batch predictions at scale
- ✅ Comprehensive model monitoring
- ✅ Kubernetes-native deployment

**Current Configuration**: Batch predictions only (real-time disabled)

**Last Updated**: October 17, 2025

---

For questions or issues, check:

- Health endpoint: `http://localhost:8000/mlops/health`
- Status endpoint: `http://localhost:8000/mlops/status`
- Swagger docs: `http://localhost:8000/docs`
