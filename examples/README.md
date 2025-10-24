# MLOps Training Script Upload Examples

This directory contains example training scripts and utilities for the MLOps platform.

## 📁 Directory Structure

```
examples/
├── training_scripts/          # Example training scripts
│   ├── sklearn_classification.py
│   ├── xgboost_regression.py
│   └── lightgbm_classification.py
├── upload_training_script.py  # Helper utility to upload scripts
└── README.md                  # This file
```

## 🚀 Quick Start

### 1. Upload a Training Script

```bash
# Start port-forward if using Kubernetes
kubectl port-forward -n asgard svc/asgard-api 8000:8000 &

# Upload sklearn classification example
python examples/upload_training_script.py \
    --script examples/training_scripts/sklearn_classification.py \
    --experiment sklearn_examples \
    --model random_forest_classifier \
    --requirements scikit-learn pandas numpy

# Upload XGBoost regression example
python examples/upload_training_script.py \
    --script examples/training_scripts/xgboost_regression.py \
    --experiment xgboost_examples \
    --model xgb_regressor \
    --requirements xgboost scikit-learn numpy

# Upload LightGBM with custom environment variables
python examples/upload_training_script.py \
    --script examples/training_scripts/lightgbm_classification.py \
    --experiment lightgbm_examples \
    --model lgbm_classifier \
    --requirements lightgbm scikit-learn pandas matplotlib \
    --env N_SAMPLES=5000 \
    --env N_FEATURES=25
```

### 2. Run Inference on Trained Model

```bash
# After training completes, run inference
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "random_forest_classifier",
    "model_version": "1",
    "inputs": {
      "feature_0": [1.5, 2.3, -0.5],
      "feature_1": [0.8, -1.2, 2.1],
      "feature_2": [-0.3, 1.7, 0.4]
    },
    "return_probabilities": true
  }'
```

## 📋 Training Script Requirements

All training scripts must follow these requirements:

### 1. Use MLflow for Tracking

```python
import mlflow

with mlflow.start_run():
    # Training code here
    pass
```

### 2. Log the Model

```python
# For sklearn
mlflow.sklearn.log_model(model, "model")

# For XGBoost
mlflow.xgboost.log_model(model, "model")

# For LightGBM
mlflow.lightgbm.log_model(model, "model")
```

### 3. Log Parameters and Metrics

```python
# Log hyperparameters
mlflow.log_params({"learning_rate": 0.01, "max_depth": 10})

# Log metrics
mlflow.log_metric("accuracy", 0.95)
mlflow.log_metric("f1_score", 0.92)
```

## 🔧 API Endpoints

### Upload Training Script

```bash
POST /mlops/training/upload
```

**Request:**

```json
{
  "script_name": "my_training_script",
  "script_content": "aW1wb3J0IG1sZmxvdw...",  # base64 encoded
  "experiment_name": "my_experiment",
  "model_name": "my_model",
  "requirements": ["scikit-learn", "pandas"],
  "environment_vars": {"DATA_PATH": "/data/train.csv"},
  "timeout": 300,
  "tags": {"version": "1.0"}
}
```

**Response:**

```json
{
  "job_id": "abc12345",
  "script_name": "my_training_script",
  "experiment_name": "my_experiment",
  "model_name": "my_model",
  "status": "queued",
  "created_at": "2025-10-23T10:00:00Z"
}
```

### Check Training Job Status

```bash
GET /mlops/training/jobs/{job_id}
```

**Response:**

```json
{
  "job_id": "abc12345",
  "script_name": "my_training_script",
  "experiment_name": "my_experiment",
  "model_name": "my_model",
  "status": "completed",
  "run_id": "xyz789",
  "model_version": "1",
  "logs": "Training logs...",
  "duration_seconds": 45.2,
  "created_at": "2025-10-23T10:00:00Z",
  "completed_at": "2025-10-23T10:00:45Z"
}
```

### Run Inference

```bash
POST /mlops/inference
```

**Request:**

```json
{
  "model_name": "my_model",
  "model_version": "1",
  "inputs": {
    "feature_1": [1.0, 2.0, 3.0],
    "feature_2": [4.0, 5.0, 6.0]
  },
  "return_probabilities": true
}
```

**Response:**

```json
{
  "model_name": "my_model",
  "model_version": "1",
  "predictions": [0, 1, 0],
  "probabilities": [
    [0.8, 0.2],
    [0.3, 0.7],
    [0.9, 0.1]
  ],
  "inference_time_ms": 12.5,
  "timestamp": "2025-10-23T10:05:00Z"
}
```

## 📚 Example Workflows

### Workflow 1: Quick Test

```bash
# 1. Upload sklearn example
python examples/upload_training_script.py \
    --script examples/training_scripts/sklearn_classification.py \
    --experiment test \
    --model test_model

# 2. Wait for completion (automatic polling)

# 3. Run inference
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{"model_name": "test_model", "inputs": {...}}'
```

### Workflow 2: Custom Training Script

```python
# my_custom_training.py
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
import pandas as pd

# Load your data
data = pd.read_csv("/path/to/data.csv")
X = data.drop("target", axis=1)
y = data["target"]

# Train with MLflow
with mlflow.start_run():
    model = LogisticRegression()
    model.fit(X, y)

    # Log model
    mlflow.sklearn.log_model(model, "model")
    mlflow.log_metric("accuracy", model.score(X, y))
```

```bash
# Upload custom script
python examples/upload_training_script.py \
    --script my_custom_training.py \
    --experiment my_experiment \
    --model my_model \
    --requirements scikit-learn pandas \
    --env DATA_PATH=/data/train.csv
```

## 🎯 Best Practices

1. **Always use `mlflow.start_run()`** - This creates a tracking context
2. **Log the model with the correct flavor** - Use `mlflow.sklearn`, `mlflow.xgboost`, etc.
3. **Include input examples** - Helps with model serving: `log_model(model, "model", input_example=X[:5])`
4. **Log comprehensive metrics** - Include accuracy, precision, recall, F1, etc.
5. **Use environment variables** - For configurable parameters like data paths
6. **Set timeouts appropriately** - Based on expected training time
7. **Handle errors gracefully** - Use try/except blocks

## 🔍 Troubleshooting

### Script fails with "No MLflow run created"

Make sure your script includes:

```python
with mlflow.start_run():
    # All training code here
    mlflow.log_model(...)
```

### Model not available for inference

Verify the model was logged:

```bash
# Check MLflow UI
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
# Open http://localhost:5000

# Or check via API
curl http://localhost:8000/mlops/models/my_model
```

### Execution timeout

Increase the timeout parameter:

```bash
python upload_training_script.py \
    --script my_script.py \
    --timeout 600  # 10 minutes
    ...
```

## 📖 Additional Resources

- **MLflow Documentation**: https://mlflow.org/docs/latest/index.html
- **MLOps API Docs**: http://localhost:8000/docs
- **Swagger UI**: http://localhost:8000/docs#/MLOps
