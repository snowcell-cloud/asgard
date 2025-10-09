# Feast Feature Store Integration

This module provides a complete feature store and ML platform built on Feast, integrated with the Asgard Data Platform.

## 🎯 Features

- **Feature Store**: Register and serve features from gold layer tables
- **ML Training**: Train models using scikit-learn, XGBoost, and more
- **Model Registry**: Version and manage trained models
- **Online Predictions**: Low-latency real-time inference
- **Batch Predictions**: High-throughput bulk scoring

## 📁 Module Structure

```
app/feast/
├── __init__.py          # Module exports
├── schemas.py           # Pydantic models for API
├── service.py           # Core feature store service
└── router.py            # FastAPI endpoints
```

## 🚀 Quick Start

### 1. Register Features

```python
POST /feast/features
{
  "name": "customer_features",
  "entities": ["customer_id"],
  "features": [
    {"name": "total_orders", "dtype": "int64"},
    {"name": "avg_order_value", "dtype": "float64"}
  ],
  "source": {
    "table_name": "customer_aggregates",
    "timestamp_field": "updated_at"
  }
}
```

### 2. Train Model

```python
POST /feast/models
{
  "name": "churn_predictor",
  "framework": "sklearn",
  "model_type": "classification",
  "training_data": {
    "entity_df_source": "customers",
    "label_column": "churned",
    "event_timestamp_column": "snapshot_date",
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z"
  }
}
```

### 3. Predict

```python
POST /feast/predictions/online
{
  "model_id": "model-uuid",
  "features": {
    "total_orders": 15,
    "avg_order_value": 83.37
  }
}
```

## 📊 API Endpoints

| Endpoint                    | Method | Description           |
| --------------------------- | ------ | --------------------- |
| `/feast/features`           | POST   | Register feature view |
| `/feast/features`           | GET    | List feature views    |
| `/feast/models`             | POST   | Train ML model        |
| `/feast/models`             | GET    | List models           |
| `/feast/predictions/online` | POST   | Online prediction     |
| `/feast/predictions/batch`  | POST   | Batch predictions     |
| `/feast/status`             | GET    | Feature store status  |

## 🏗️ Architecture

```
Gold Layer (Trino/Iceberg)
        ↓
Feast Feature Store
  ├── Registry (SQLite)
  ├── Online Store (SQLite)
  └── Offline Store (Trino)
        ↓
ML Models (scikit-learn/XGBoost)
        ↓
Predictions (Online/Batch)
```

## 🔧 Configuration

Environment variables:

```bash
# Feast
FEAST_REPO_PATH=/tmp/feast_repo
MODEL_STORAGE_PATH=/tmp/models

# Trino
TRINO_HOST=trino.data-platform.svc.cluster.local
TRINO_PORT=8080
TRINO_USER=dbt
TRINO_CATALOG=iceberg
GOLD_SCHEMA=gold
```

## 📚 Documentation

- [Full Documentation](../docs/FEAST_FEATURE_STORE.md)
- [Quick Start Guide](../docs/FEAST_QUICK_START.md)
- [Postman Collection](../docs/postman/feast_api_collection.json)

## 🧪 Supported ML Frameworks

- **scikit-learn**: RandomForest, GradientBoosting
- **XGBoost**: Classification and Regression
- **LightGBM**: (Coming soon)
- **TensorFlow**: (Coming soon)
- **PyTorch**: (Coming soon)

## 🎓 Examples

See [Quick Start Guide](../docs/FEAST_QUICK_START.md) for complete examples including:

- Customer churn prediction
- Order value forecasting
- Production volume prediction
- Real-time and batch scoring

## 🔍 Implementation Details

### Feature Store Service (`service.py`)

- **FeatureStoreService**: Main service class
  - `create_feature_view()`: Register features from gold layer
  - `train_model()`: Train ML models with historical features
  - `predict_online()`: Real-time predictions
  - `predict_batch()`: Bulk scoring

### Schemas (`schemas.py`)

- Request/response models for all endpoints
- Enum types for frameworks, model types, etc.
- Validation rules for data integrity

### Router (`router.py`)

- FastAPI endpoints with OpenAPI documentation
- Dependency injection for service
- Comprehensive error handling

## 🚦 Status Codes

- `200`: Success
- `201`: Resource created
- `400`: Bad request (validation error)
- `404`: Resource not found
- `500`: Server error

## 📈 Metrics & Monitoring

Models return comprehensive metrics:

**Classification:**

- Accuracy
- F1 Score
- Precision/Recall

**Regression:**

- MSE (Mean Squared Error)
- R² Score
- MAE (Mean Absolute Error)

## 🔐 Security

- Input validation via Pydantic
- SQL injection prevention
- Model artifact isolation
- Feature access control (planned)

## 🛠️ Development

Run locally:

```bash
# Install dependencies
uv sync

# Run server
uv run uvicorn app.main:app --reload

# Access API docs
open http://localhost:8000/docs
```

## 📝 License

Part of Asgard Data Platform
