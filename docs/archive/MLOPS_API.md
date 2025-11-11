# MLOps API - Simplified Documentation

**Version**: 5.0.0  
**Last Updated**: October 23, 2025

---

## 📋 Overview

Simple, flexible MLOps API for script-based training and model serving.

**Core Philosophy**: Upload Python scripts (.py files) → Track training → Serve models

---

## 🌐 API Endpoints

### Training & Job Management

#### 1. Upload Training Script

```http
POST /mlops/training/upload
```

Upload a Python training script for execution.

**Request**:

```json
{
  "script_name": "my_training.py",
  "script_content": "import mlflow\nimport mlflow.sklearn...",
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "requirements": ["scikit-learn", "pandas"],
  "environment_vars": {
    "DATA_PATH": "/data/train.csv"
  },
  "timeout": 300,
  "tags": { "version": "1.0" }
}
```

**Response** (202 Accepted):

```json
{
  "job_id": "abc-123-def",
  "script_name": "my_training.py",
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "status": "queued",
  "created_at": "2025-10-23T10:00:00Z"
}
```

#### 2. Check Training Job Status

```http
GET /mlops/training/jobs/{job_id}
```

**Response**:

```json
{
  "job_id": "abc-123-def",
  "script_name": "my_training.py",
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "status": "completed",
  "run_id": "mlflow-run-id",
  "model_version": "1",
  "logs": "Training started...\nEpoch 1/10...",
  "error": null,
  "created_at": "2025-10-23T10:00:00Z",
  "started_at": "2025-10-23T10:00:05Z",
  "completed_at": "2025-10-23T10:05:30Z",
  "duration_seconds": 325.5
}
```

**Status Values**:

- `queued` - Job is waiting to start
- `running` - Training in progress
- `completed` - Training finished successfully
- `failed` - Training failed with error

---

### Model Inference

#### 3. Run Inference

```http
POST /mlops/inference
```

Make predictions using a trained model.

**Request**:

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "inputs": {
    "age": [25, 35, 45],
    "income": [50000, 75000, 100000],
    "tenure": [1, 5, 10]
  },
  "return_probabilities": true
}
```

**Response**:

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "predictions": [1, 0, 0],
  "probabilities": [
    [0.2, 0.8],
    [0.9, 0.1],
    [0.95, 0.05]
  ],
  "inference_time_ms": 15.3,
  "timestamp": "2025-10-23T10:10:00Z"
}
```

---

### Model Registry

#### 4. Register Model (Manual)

```http
POST /mlops/registry
```

Manually register a model from an MLflow run.

**Request**:

```json
{
  "model_name": "churn_predictor",
  "run_id": "mlflow-run-id-123",
  "description": "Production model v2.0",
  "tags": {
    "data_version": "2025-10",
    "trained_by": "john.doe"
  }
}
```

**Response** (201 Created):

```json
{
  "model_name": "churn_predictor",
  "version": "2",
  "run_id": "mlflow-run-id-123",
  "status": "registered",
  "created_at": "2025-10-23T10:15:00Z"
}
```

#### 5. List Models

```http
GET /mlops/models
```

**Response**:

```json
[
  {
    "name": "churn_predictor",
    "description": "Customer churn prediction model",
    "tags": { "team": "data-science" },
    "latest_versions": [
      {
        "name": "churn_predictor",
        "version": "2",
        "stage": "None",
        "run_id": "mlflow-run-id-123",
        "created_at": "2025-10-23T10:15:00Z",
        "updated_at": "2025-10-23T10:15:00Z"
      }
    ],
    "created_at": "2025-10-20T08:00:00Z",
    "updated_at": "2025-10-23T10:15:00Z"
  }
]
```

#### 6. Get Model Details

```http
GET /mlops/models/{model_name}
```

**Response**: Same structure as item in list above.

---

### System Status

#### 7. Platform Status

```http
GET /mlops/status
```

**Response**:

```json
{
  "mlflow_tracking_uri": "http://mlflow-service:5000",
  "mlflow_available": true,
  "feast_store_available": true,
  "registered_models": 15,
  "active_experiments": 8,
  "feature_views": 12,
  "timestamp": "2025-10-23T10:20:00Z"
}
```

---

## 📝 Training Script Requirements

Your Python script **must**:

1. Import and use MLflow:

```python
import mlflow
import mlflow.sklearn  # or xgboost, lightgbm, tensorflow, etc.
```

2. Start an MLflow run:

```python
with mlflow.start_run():
    # Your training code here
```

3. Log the trained model:

```python
mlflow.sklearn.log_model(model, "model")
# or mlflow.xgboost.log_model(model, "model")
# or mlflow.lightgbm.log_model(model, "model")
```

### Complete Example Script

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import os

# Load data (from anywhere - S3, DB, local file, etc.)
X, y = make_classification(
    n_samples=int(os.getenv("N_SAMPLES", "1000")),
    n_features=20,
    random_state=42
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)

    # Train
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)

    # Log model (REQUIRED!)
    mlflow.sklearn.log_model(model, "model")

    print(f"✅ Training complete! Accuracy: {accuracy:.3f}")
```

---

## 🚀 Quick Start

### 1. Prepare Your Script

Create `train.py` with your ML code (see example above).

### 2. Upload Script

```bash
# Using curl
curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train.py",
    "script_content": "'"$(cat train.py)"'",
    "experiment_name": "my_experiment",
    "model_name": "my_model",
    "requirements": ["scikit-learn"]
  }'

# Or use the helper utility
python examples/upload_training_script.py \
  --script train.py \
  --experiment my_experiment \
  --model my_model \
  --requirements scikit-learn
```

### 3. Check Status

```bash
curl http://localhost:8000/mlops/training/jobs/{job_id}
```

### 4. Run Inference

```bash
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "my_model",
    "model_version": "1",
    "inputs": {
      "feature_0": [1.0, 2.0],
      "feature_1": [3.0, 4.0]
    }
  }'
```

---

## 🔧 Advanced Features

### Environment Variables

Pass configuration to your training script:

```json
{
  "script_name": "train.py",
  "script_content": "...",
  "environment_vars": {
    "DATA_PATH": "s3://bucket/data.csv",
    "N_ESTIMATORS": "200",
    "LEARNING_RATE": "0.01"
  }
}
```

Access in script:

```python
import os

data_path = os.getenv("DATA_PATH")
n_estimators = int(os.getenv("N_ESTIMATORS", "100"))
learning_rate = float(os.getenv("LEARNING_RATE", "0.1"))
```

### Custom Requirements

Install specific package versions:

```json
{
  "requirements": ["scikit-learn==1.3.0", "xgboost>=2.0.0", "pandas", "s3fs"]
}
```

### Timeout Configuration

Set maximum execution time (60-3600 seconds):

```json
{
  "timeout": 600
}
```

---

## 📊 Response Codes

| Code | Meaning      | Description             |
| ---- | ------------ | ----------------------- |
| 200  | OK           | Request successful      |
| 201  | Created      | Resource created        |
| 202  | Accepted     | Job queued successfully |
| 400  | Bad Request  | Invalid input           |
| 404  | Not Found    | Resource doesn't exist  |
| 500  | Server Error | Internal error          |

---

## 🔍 Error Handling

### Training Failed

```json
{
  "job_id": "abc-123",
  "status": "failed",
  "error": "ModuleNotFoundError: No module named 'xgboost'",
  "logs": "pip install scikit-learn\nRunning training...\nError occurred"
}
```

**Common Causes**:

- Missing `requirements` in upload request
- Script syntax errors
- Missing `mlflow.log_model()` call
- Timeout exceeded

### Inference Error

```json
{
  "detail": "Model my_model version 999 not found"
}
```

---

## 💡 Best Practices

### 1. Always Log Your Model

```python
# ❌ Wrong - model not saved
with mlflow.start_run():
    model.fit(X, y)
    # No mlflow.log_model() call!

# ✅ Correct
with mlflow.start_run():
    model.fit(X, y)
    mlflow.sklearn.log_model(model, "model")
```

### 2. Handle Data Loading Gracefully

```python
try:
    # Load from S3, database, etc.
    X, y = load_data_from_source()
except Exception as e:
    print(f"Error loading data: {e}")
    raise  # Let MLOps service capture the error
```

### 3. Log Comprehensive Metrics

```python
mlflow.log_metrics({
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "f1_score": f1,
    "training_time": time_taken
})
```

### 4. Use Environment Variables

```python
# Makes scripts reusable
n_samples = int(os.getenv("N_SAMPLES", "1000"))
test_size = float(os.getenv("TEST_SIZE", "0.2"))
```

### 5. Print Progress

```python
print("Loading data...")
print(f"Training with {len(X_train)} samples...")
print("Evaluating model...")
print(f"✅ Complete! Accuracy: {accuracy:.3f}")
```

These prints appear in job logs!

---

## 🛠️ Helper Utilities

### Upload Script CLI

Located at `examples/upload_training_script.py`:

```bash
python examples/upload_training_script.py \
  --script path/to/train.py \
  --experiment my_experiment \
  --model my_model \
  --requirements scikit-learn pandas \
  --env DATA_PATH=/data/train.csv \
  --env N_ESTIMATORS=200 \
  --timeout 600
```

Features:

- Automatic base64 encoding
- Job status polling
- Live log display
- Duration tracking

---

## 📚 Example Scripts

See `examples/training_scripts/` for complete examples:

- `sklearn_classification.py` - Random Forest classifier
- `xgboost_regression.py` - XGBoost regressor
- `lightgbm_classification.py` - LightGBM with env vars

---

## 🔗 Related Documentation

- [Complete Feature Guide](./SCRIPT_TRAINING_INFERENCE.md)
- [API Cleanup Summary](./API_CLEANUP_SUMMARY.md)
- [Implementation Summary](./SCRIPT_TRAINING_IMPLEMENTATION.md)

---

**API Base URL**: `http://localhost:8000` (development)  
**API Docs (Swagger)**: `http://localhost:8000/docs`  
**Version**: 5.0.0
