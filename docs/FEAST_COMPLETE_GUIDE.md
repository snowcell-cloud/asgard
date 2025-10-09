# Asgard Feast Feature Store - Complete Guide

> **Complete documentation for the Asgard Feast Feature Store implementation**  
> Last Updated: October 9, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [API Reference](#api-reference)
5. [Feast UI](#feast-ui)
6. [Feature Registration](#feature-registration)
7. [Model Training](#model-training)
8. [Making Predictions](#making-predictions)
9. [Troubleshooting](#troubleshooting)
10. [Production Deployment](#production-deployment)

---

## Overview

### What is Asgard Feast?

Asgard Feast is a production-ready feature store implementation that:

- ✅ Integrates with Trino/Iceberg gold layer
- ✅ Provides REST APIs for feature management
- ✅ Supports ML model training and versioning
- ✅ Enables online and batch predictions
- ✅ Includes Feast UI for visualization

### Key Features

| Feature                    | Description                                     |
| -------------------------- | ----------------------------------------------- |
| **Gold Layer Integration** | Automatically syncs features from Trino/Iceberg |
| **REST API**               | FastAPI endpoints for all operations            |
| **Feature Registry**       | SQLite-based registry for metadata              |
| **Online Store**           | SQLite for low-latency feature serving          |
| **Offline Store**          | Parquet files synced from Trino                 |
| **ML Framework Support**   | scikit-learn, XGBoost integration               |
| **Feast UI**               | Web interface for browsing features             |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Asgard Data Platform                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Gold Layer (Trino + Iceberg)                          │
│           ↓                                            │
│  FastAPI REST API (app/feast/)                        │
│  ├── POST /feast/features    → Register features       │
│  ├── POST /feast/models      → Train ML models        │
│  └── POST /feast/predictions → Get predictions        │
│           ↓                                            │
│  Feast Feature Store (/tmp/feast_repo)                │
│  ├── Registry (SQLite)                                │
│  ├── Online Store (SQLite)                            │
│  └── Offline Store (Parquet)                          │
│           ↓                                            │
│  Feast UI (http://localhost:8888)                     │
│  └── Browse & manage features                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- UV package manager
- Access to Trino/Iceberg (optional for demo)

### 1. Launch Feast UI

```bash
# Start the Feast UI with sample features
cd /home/hac/downloads/code/asgard-dev
./start-asgard-feast-ui.sh
```

Open browser: **http://localhost:8888**

### 2. Start Asgard API

```bash
# In a new terminal
cd /home/hac/downloads/code/asgard-dev
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open API docs: **http://localhost:8000/docs**

### 3. Register Your First Feature

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_features",
    "entities": ["customer_id"],
    "features": [
      {"name": "total_purchases", "dtype": "FLOAT64"},
      {"name": "avg_purchase_value", "dtype": "FLOAT64"}
    ],
    "source": {
      "table_name": "customer_aggregates",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "online": true
  }'
```

### 4. View in Feast UI

Refresh the Feast UI to see your newly registered features!

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Data Sources                          │
├─────────────────────────────────────────────────────────┤
│  Trino + Iceberg (iceberg.gold schema)                 │
│  └── Tables: customer_aggregates, product_stats, etc.  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│               Asgard API Layer                          │
├─────────────────────────────────────────────────────────┤
│  app/feast/router.py    - FastAPI endpoints            │
│  app/feast/service.py   - Business logic               │
│  app/feast/schemas.py   - Pydantic models              │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                Data Sync Layer                          │
├─────────────────────────────────────────────────────────┤
│  _sync_trino_to_parquet()                              │
│  ├── Query Trino table                                 │
│  ├── Convert to DataFrame                              │
│  └── Save to /tmp/feast_repo/data/*.parquet           │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Feast Feature Store                        │
├─────────────────────────────────────────────────────────┤
│  Registry:       /tmp/feast_repo/data/registry.db      │
│  Online Store:   /tmp/feast_repo/data/online_store.db  │
│  Offline Store:  /tmp/feast_repo/data/*.parquet        │
│  Config:         /tmp/feast_repo/feature_store.yaml    │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                Feast UI & Serving                       │
├─────────────────────────────────────────────────────────┤
│  Feast UI:         http://localhost:8888               │
│  Online Features:  POST /feast/predictions/online      │
│  Batch Features:   POST /feast/predictions/batch       │
└─────────────────────────────────────────────────────────┘
```

### File Structure

```
asgard-dev/
├── app/
│   └── feast/
│       ├── __init__.py
│       ├── router.py          # 9 FastAPI endpoints
│       ├── service.py         # Core FeatureStoreService
│       └── schemas.py         # Pydantic models
│
├── docs/
│   └── FEAST_COMPLETE_GUIDE.md   # This file
│
├── setup_feast_repo.py        # Setup script for Feast repo
├── start-asgard-feast-ui.sh   # Launch Feast UI
│
└── /tmp/feast_repo/           # Feast repository
    ├── feature_store.yaml     # Feast configuration
    ├── feature_definitions.py # Feature views
    └── data/
        ├── registry.db        # Feature registry
        ├── online_store.db    # SQLite online store
        └── *.parquet          # Offline feature data
```

---

## API Reference

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Register Feature View

**POST** `/feast/features`

Register a new feature view from a gold layer table.

**Request:**

```json
{
  "name": "customer_features",
  "entities": ["customer_id"],
  "features": [
    {
      "name": "total_purchases",
      "dtype": "FLOAT64",
      "description": "Total purchase amount"
    },
    {
      "name": "last_purchase_days",
      "dtype": "INT64"
    }
  ],
  "source": {
    "table_name": "customer_aggregates",
    "catalog": "iceberg",
    "schema": "gold",
    "timestamp_field": "event_timestamp"
  },
  "description": "Customer purchasing features",
  "online": true,
  "ttl_seconds": 86400,
  "tags": {
    "team": "analytics",
    "domain": "customer"
  }
}
```

**Response:**

```json
{
  "name": "customer_features",
  "status": "registered",
  "feature_count": 2,
  "entity_count": 1,
  "online_enabled": true,
  "created_at": "2025-10-09T10:30:00Z",
  "message": "Feature view registered successfully"
}
```

#### 2. List Feature Views

**GET** `/feast/features`

List all registered feature views.

**Response:**

```json
{
  "feature_views": [
    {
      "name": "customer_features",
      "entities": ["customer_id"],
      "feature_count": 2,
      "online": true,
      "created_at": "2025-10-09T10:30:00Z"
    }
  ],
  "total_count": 1
}
```

#### 3. Get Feature View Details

**GET** `/feast/features/{feature_view_name}`

Get detailed information about a specific feature view.

**Response:**

```json
{
  "name": "customer_features",
  "entities": ["customer_id"],
  "features": [
    {
      "name": "total_purchases",
      "dtype": "FLOAT64",
      "description": "Total purchase amount"
    }
  ],
  "source": {
    "table_name": "customer_aggregates",
    "catalog": "iceberg",
    "schema": "gold"
  },
  "online": true,
  "ttl_seconds": 86400,
  "tags": {
    "team": "analytics"
  }
}
```

#### 4. Train ML Model

**POST** `/feast/models`

Train a machine learning model using features from the feature store.

**Request:**

```json
{
  "model_name": "churn_predictor_v1",
  "model_type": "BINARY_CLASSIFICATION",
  "framework": "SKLEARN_RANDOM_FOREST",
  "feature_views": ["customer_features", "usage_features"],
  "target_column": "churned",
  "training_dataset": {
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-09-01T00:00:00Z"
  },
  "hyperparameters": {
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5
  },
  "description": "Customer churn prediction model"
}
```

**Response:**

```json
{
  "model_id": "churn_predictor_v1_20251009_103000",
  "model_name": "churn_predictor_v1",
  "version": "1.0.0",
  "status": "trained",
  "metrics": {
    "accuracy": 0.92,
    "precision": 0.89,
    "recall": 0.88,
    "f1_score": 0.885
  },
  "trained_at": "2025-10-09T10:30:00Z",
  "model_path": "/tmp/models/churn_predictor_v1_20251009_103000.pkl"
}
```

#### 5. List Models

**GET** `/feast/models`

List all trained models.

**Response:**

```json
{
  "models": [
    {
      "model_id": "churn_predictor_v1_20251009_103000",
      "model_name": "churn_predictor_v1",
      "version": "1.0.0",
      "model_type": "BINARY_CLASSIFICATION",
      "trained_at": "2025-10-09T10:30:00Z"
    }
  ],
  "total_count": 1
}
```

#### 6. Get Model Details

**GET** `/feast/models/{model_id}`

Get detailed information about a trained model.

#### 7. Online Predictions

**POST** `/feast/predictions/online`

Get real-time predictions using online feature store.

**Request:**

```json
{
  "model_id": "churn_predictor_v1_20251009_103000",
  "entities": {
    "customer_id": [101, 102, 103]
  },
  "features": [
    "customer_features:total_purchases",
    "customer_features:last_purchase_days"
  ]
}
```

**Response:**

```json
{
  "predictions": [
    {
      "customer_id": 101,
      "prediction": 0.12,
      "prediction_class": 0,
      "features_used": {
        "total_purchases": 1250.5,
        "last_purchase_days": 5
      }
    }
  ],
  "model_id": "churn_predictor_v1_20251009_103000",
  "timestamp": "2025-10-09T10:30:00Z"
}
```

#### 8. Batch Predictions

**POST** `/feast/predictions/batch`

Get batch predictions for a dataset.

**Request:**

```json
{
  "model_id": "churn_predictor_v1_20251009_103000",
  "entity_dataset": {
    "start_date": "2025-10-01T00:00:00Z",
    "end_date": "2025-10-09T00:00:00Z"
  },
  "output_format": "parquet"
}
```

#### 9. Get Feature Store Status

**GET** `/feast/status`

Get the current status of the feature store.

**Response:**

```json
{
  "status": "healthy",
  "feature_views_count": 3,
  "entities_count": 2,
  "models_count": 1,
  "online_store": "sqlite",
  "registry_path": "/tmp/feast_repo/data/registry.db"
}
```

---

## Feast UI

### Accessing the UI

#### Quick Launch

```bash
./start-asgard-feast-ui.sh
```

#### Manual Launch

```bash
cd /tmp/feast_repo
/home/hac/downloads/code/asgard-dev/.venv/bin/feast ui -h 0.0.0.0 -p 8888
```

Then open: **http://localhost:8888**

### UI Features

#### 1. Feature Views Tab

- Browse all registered feature views
- View feature schemas and data types
- See entity relationships
- Check TTL settings and tags

#### 2. Entities Tab

- View all entities
- See join keys
- Check entity descriptions

#### 3. Feature Services Tab

- Browse feature services
- See feature groupings
- View service metadata

#### 4. Data Sources Tab

- View configured data sources
- Check connection details
- See source types (FileSource, TrinoSource, etc.)

### Sample Features Included

The setup includes 3 pre-configured feature views:

**Customer Features:**

```yaml
Name: customer_features
Entity: customer
Features:
  - total_purchases (Float64)
  - avg_purchase_value (Float64)
  - last_purchase_days_ago (Int64)
TTL: 1 day
Online: Yes
```

**Product Features:**

```yaml
Name: product_features
Entity: product
Features:
  - total_sales (Float64)
  - avg_rating (Float64)
  - review_count (Int64)
TTL: 7 days
Online: Yes
```

**Order Features:**

```yaml
Name: order_features
Entity: order
Features:
  - order_total (Float64)
  - item_count (Int64)
  - is_completed (Int64)
TTL: 12 hours
Online: Yes
```

---

## Feature Registration

### From Gold Layer (Recommended)

Register features directly from your Trino/Iceberg gold layer:

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "product_analytics",
    "entities": ["product_id"],
    "features": [
      {"name": "views_30d", "dtype": "INT64"},
      {"name": "conversion_rate", "dtype": "FLOAT64"},
      {"name": "revenue_30d", "dtype": "FLOAT64"}
    ],
    "source": {
      "table_name": "product_metrics",
      "catalog": "iceberg",
      "schema": "gold",
      "timestamp_field": "event_timestamp"
    },
    "online": true,
    "ttl_seconds": 3600
  }'
```

### What Happens

1. **Validation**: API validates the gold layer table exists
2. **Data Sync**: Queries Trino and syncs data to Parquet
3. **Feature Registration**: Creates FileSource and FeatureView
4. **Registry Update**: Registers with Feast registry
5. **Online Store**: (Optional) Materializes to online store

### Data Sync Process

```python
# Service automatically syncs data
def _sync_trino_to_parquet(table_fqn, feature_view_name):
    # 1. Query Trino
    df = pd.read_sql(f"SELECT * FROM {table_fqn}", trino_conn)

    # 2. Save to Parquet
    parquet_path = f"/tmp/feast_repo/data/{feature_view_name}.parquet"
    df.to_parquet(parquet_path)

    # 3. Return path for FileSource
    return parquet_path
```

### Feature Types

Supported data types:

| Feast Type       | Python Type | Example             |
| ---------------- | ----------- | ------------------- |
| `FLOAT32`        | float       | 3.14                |
| `FLOAT64`        | float       | 3.141592653         |
| `INT32`          | int         | 42                  |
| `INT64`          | int         | 9223372036854775807 |
| `STRING`         | str         | "example"           |
| `BOOL`           | bool        | true                |
| `UNIX_TIMESTAMP` | int         | 1696838400          |

---

## Model Training

### Supported Frameworks

| Framework        | Model Types                                        |
| ---------------- | -------------------------------------------------- |
| **scikit-learn** | RandomForest, LogisticRegression, GradientBoosting |
| **XGBoost**      | XGBClassifier, XGBRegressor                        |

### Training Example

```bash
curl -X POST http://localhost:8000/feast/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "product_recommender",
    "model_type": "REGRESSION",
    "framework": "XGBOOST",
    "feature_views": [
      "customer_features",
      "product_features"
    ],
    "target_column": "purchase_probability",
    "training_dataset": {
      "start_date": "2025-01-01T00:00:00Z",
      "end_date": "2025-09-01T00:00:00Z"
    },
    "hyperparameters": {
      "max_depth": 6,
      "learning_rate": 0.1,
      "n_estimators": 100,
      "objective": "reg:squarederror"
    }
  }'
```

### Training Process

1. **Feature Retrieval**: Fetches historical features from offline store
2. **Dataset Creation**: Creates training dataset with target
3. **Model Training**: Trains using specified framework
4. **Validation**: Evaluates on validation set
5. **Model Saving**: Saves model with metadata
6. **Metrics Recording**: Stores performance metrics

### Model Versioning

Models are automatically versioned:

```
Format: {model_name}_{timestamp}
Example: product_recommender_20251009_103000

Stored at: /tmp/models/{model_id}.pkl
```

---

## Making Predictions

### Online Predictions (Real-time)

For low-latency predictions:

```bash
curl -X POST http://localhost:8000/feast/predictions/online \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "product_recommender_20251009_103000",
    "entities": {
      "customer_id": [101, 102],
      "product_id": [501, 502]
    },
    "features": [
      "customer_features:total_purchases",
      "product_features:avg_rating"
    ]
  }'
```

**Response time**: < 100ms

### Batch Predictions

For large-scale scoring:

```bash
curl -X POST http://localhost:8000/feast/predictions/batch \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "product_recommender_20251009_103000",
    "entity_dataset": {
      "start_date": "2025-10-01T00:00:00Z",
      "end_date": "2025-10-09T00:00:00Z"
    },
    "output_format": "parquet",
    "output_path": "/tmp/predictions/batch_20251009.parquet"
  }'
```

---

## Troubleshooting

### Common Issues

#### 1. Feast UI Shows No Features

**Problem**: UI is empty after startup

**Solution**:

```bash
cd /tmp/feast_repo
/home/hac/downloads/code/asgard-dev/.venv/bin/feast apply
/home/hac/downloads/code/asgard-dev/.venv/bin/feast feature-views list
```

#### 2. Import Error: Cannot import TrinoSource

**Problem**:

```
ImportError: cannot import name 'TrinoSource' from 'feast'
```

**Solution**: Already fixed! The implementation uses FileSource with Trino sync.

**Details**: See the data sync approach in `app/feast/service.py`:

```python
# Syncs Trino data to Parquet
parquet_path = self._sync_trino_to_parquet(table_fqn, request.name)

# Uses FileSource instead of TrinoSource
source = FileSource(
    name=f"{request.name}_source",
    path=parquet_path,
    timestamp_field=request.source.timestamp_field
)
```

#### 3. Pydantic Warning: Field "schema" shadows BaseModel

**Problem**:

```
UserWarning: Field name "schema" in "DataSourceConfig" shadows an attribute
```

**Solution**: Already fixed! Using `schema_name` with alias:

```python
class DataSourceConfig(BaseModel):
    model_config = {"populate_by_name": True}
    schema_name: str = Field(default="gold", alias="schema")
```

#### 4. Cannot Connect to Trino

**Problem**: Features can't be registered from gold layer

**Solution**:

```bash
# Check Trino connection
curl http://trino-host:8080/v1/info

# Or port-forward if in Kubernetes
kubectl port-forward svc/trino -n data-platform 8080:8080

# Update environment variables
export TRINO_HOST=localhost
export TRINO_PORT=8080
```

#### 5. UI Port Already in Use

**Problem**: Port 8888 is already in use

**Solution**:

```bash
# Use different port
export FEAST_UI_PORT=8889
./start-asgard-feast-ui.sh

# Or kill existing process
pkill -f "feast ui"
```

#### 6. Missing Dependencies

**Problem**: `pyarrow` or other packages not found

**Solution**:

```bash
cd /home/hac/downloads/code/asgard-dev
uv add pyarrow feast scikit-learn xgboost pandas trino
```

### Debug Commands

```bash
# Check feature store status
curl http://localhost:8000/feast/status

# List features via CLI
cd /tmp/feast_repo
/home/hac/downloads/code/asgard-dev/.venv/bin/feast feature-views list

# Check registry
sqlite3 /tmp/feast_repo/data/registry.db ".tables"

# View logs
# API logs: stdout where uvicorn is running
# UI logs: stdout where feast ui is running
```

---

## Production Deployment

### Kubernetes Deployment

#### 1. ConfigMap for Feast Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feast-config
  namespace: data-platform
data:
  feature_store.yaml: |
    project: asgard_feast_prod
    registry: /data/registry.db
    provider: local
    online_store:
      type: redis
      connection_string: redis://redis-service:6379
    offline_store:
      type: file
```

#### 2. PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: feast-data
  namespace: data-platform
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
  storageClassName: standard
```

#### 3. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asgard-api
  namespace: data-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: asgard-api
  template:
    metadata:
      labels:
        app: asgard-api
    spec:
      containers:
        - name: api
          image: asgard-api:latest
          ports:
            - containerPort: 8000
          env:
            - name: FEAST_REPO_PATH
              value: "/data/feast_repo"
            - name: TRINO_HOST
              value: "trino.data-platform.svc.cluster.local"
            - name: TRINO_PORT
              value: "8080"
          volumeMounts:
            - name: feast-data
              mountPath: /data
            - name: feast-config
              mountPath: /data/feast_repo
      volumes:
        - name: feast-data
          persistentVolumeClaim:
            claimName: feast-data
        - name: feast-config
          configMap:
            name: feast-config
```

#### 4. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: asgard-api
  namespace: data-platform
spec:
  selector:
    app: asgard-api
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

#### 5. Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: asgard-api
  namespace: data-platform
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - feast.yourdomain.com
      secretName: feast-tls
  rules:
    - host: feast.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: asgard-api
                port:
                  number: 8000
```

### Environment Variables

```bash
# Feast Configuration
FEAST_REPO_PATH=/data/feast_repo
MODEL_STORAGE_PATH=/data/models

# Trino Configuration
TRINO_HOST=trino.data-platform.svc.cluster.local
TRINO_PORT=8080
TRINO_USER=feast
TRINO_CATALOG=iceberg
GOLD_SCHEMA=gold

# Redis (for production online store)
REDIS_HOST=redis.data-platform.svc.cluster.local
REDIS_PORT=6379

# API Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Production Checklist

- [ ] Use Redis for online store (not SQLite)
- [ ] Use remote registry (S3/GCS, not local file)
- [ ] Set up monitoring and alerting
- [ ] Configure backup for feature registry
- [ ] Enable authentication and authorization
- [ ] Set up CI/CD for feature deployment
- [ ] Configure rate limiting
- [ ] Enable API key authentication
- [ ] Set up logging aggregation
- [ ] Configure auto-scaling

### Monitoring

```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram

feature_requests = Counter(
    'feast_feature_requests_total',
    'Total feature requests',
    ['feature_view', 'status']
)

prediction_latency = Histogram(
    'feast_prediction_latency_seconds',
    'Prediction latency in seconds',
    ['model_id']
)
```

---

## Best Practices

### 1. Feature Naming

```python
# Good
customer_lifetime_value
product_avg_rating_30d
order_total_last_7d

# Bad
clv
rating
total
```

### 2. Entity Design

```python
# Use consistent join keys
customer = Entity(
    name="customer",
    join_keys=["customer_id"],  # Always use same key name
    description="Customer entity"
)
```

### 3. TTL Configuration

```python
# Real-time features: Short TTL
realtime_features = FeatureView(
    ttl=timedelta(hours=1)  # 1 hour
)

# Batch features: Longer TTL
batch_features = FeatureView(
    ttl=timedelta(days=7)  # 1 week
)
```

### 4. Feature Versioning

```python
# Version your feature views
customer_features_v1
customer_features_v2

# Use feature services for models
driver_activity_v1 = FeatureService(
    name="driver_activity_v1",
    features=[customer_features_v1]
)
```

### 5. Data Validation

```python
# Validate before registration
assert len(features) > 0, "Must have at least one feature"
assert table_exists(table_fqn), "Table must exist in gold layer"
```

---

## Scripts Reference

### setup_feast_repo.py

Sets up the Feast repository with sample features.

```bash
uv run python setup_feast_repo.py
```

**Creates:**

- `/tmp/feast_repo/` directory structure
- Sample data (customer, product, order features)
- Feature definitions
- Feast configuration

### start-asgard-feast-ui.sh

Launches the Feast UI.

```bash
./start-asgard-feast-ui.sh
```

**Does:**

- Checks if setup is needed
- Lists current features
- Starts UI on port 8888
- Shows helpful instructions

---

## API Client Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Register features
response = requests.post(
    f"{BASE_URL}/feast/features",
    json={
        "name": "user_features",
        "entities": ["user_id"],
        "features": [
            {"name": "age", "dtype": "INT64"},
            {"name": "income", "dtype": "FLOAT64"}
        ],
        "source": {
            "table_name": "users",
            "catalog": "iceberg",
            "schema": "gold"
        },
        "online": True
    }
)

# Train model
response = requests.post(
    f"{BASE_URL}/feast/models",
    json={
        "model_name": "classifier_v1",
        "model_type": "BINARY_CLASSIFICATION",
        "framework": "SKLEARN_RANDOM_FOREST",
        "feature_views": ["user_features"],
        "target_column": "converted"
    }
)

# Get predictions
response = requests.post(
    f"{BASE_URL}/feast/predictions/online",
    json={
        "model_id": "classifier_v1_20251009",
        "entities": {"user_id": [1, 2, 3]},
        "features": ["user_features:age", "user_features:income"]
    }
)
predictions = response.json()
```

### cURL Examples

See [API Reference](#api-reference) section for detailed cURL examples.

---

## Summary

### What We've Built

✅ **Complete Feature Store**: Full Feast implementation with gold layer integration  
✅ **REST API**: 9 endpoints for all feature store operations  
✅ **ML Integration**: Model training and prediction capabilities  
✅ **Web UI**: Feast UI for feature visualization  
✅ **Production Ready**: Docker, Kubernetes, and Helm support

### Key Files

| File                           | Purpose             |
| ------------------------------ | ------------------- |
| `app/feast/router.py`          | FastAPI endpoints   |
| `app/feast/service.py`         | Core business logic |
| `app/feast/schemas.py`         | Pydantic models     |
| `setup_feast_repo.py`          | Feast repo setup    |
| `start-asgard-feast-ui.sh`     | UI launcher         |
| `docs/FEAST_COMPLETE_GUIDE.md` | This guide          |

### Quick Links

- **API Docs**: http://localhost:8000/docs
- **Feast UI**: http://localhost:8888
- **GitHub**: https://github.com/snowcell-cloud/asgard-dev
- **Feast Docs**: https://docs.feast.dev

---

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review API docs at http://localhost:8000/docs
3. Check Feast UI for feature status
4. Review application logs

---

**Last Updated**: October 9, 2025  
**Version**: 2.1.0  
**Maintained by**: Asgard Data Platform Team
