# Script-Based Training & Inference - Complete Guide

**Version**: 4.0.0  
**Last Updated**: October 23, 2025  
**Feature**: Upload arbitrary Python training scripts and deploy models

---

## 🎯 Overview

The Asgard MLOps platform now supports **script-based training**, allowing users to upload arbitrary Python code that trains ML models and automatically deploys them to MLflow for inference.

### Key Features

✅ **Upload any Python training script** - Support for sklearn, XGBoost, LightGBM, TensorFlow, PyTorch  
✅ **Automatic MLflow integration** - Scripts are executed with MLflow tracking pre-configured  
✅ **Isolated execution environment** - Each script runs in its own temporary workspace  
✅ **Custom dependencies** - Specify pip packages to install before execution  
✅ **Environment variables** - Pass configuration to scripts via env vars  
✅ **Job status tracking** - Poll training progress and view execution logs  
✅ **Model inference endpoint** - Serve deployed models via REST API

---

## 🏗️ Architecture

```
User uploads .py file
        ↓
POST /mlops/training/upload
        ↓
Base64 encode script
        ↓
Background execution thread
        ↓
├─ Install requirements (pip)
├─ Inject MLflow config
├─ Execute Python script
├─ Log to MLflow
├─ Register model
└─ Return job status
        ↓
Model available at POST /mlops/inference
```

### Execution Flow

1. **Upload**: User uploads Python script (base64 encoded or plain text)
2. **Queue**: Job queued with unique ID
3. **Setup**: Install specified pip packages
4. **Execute**: Run script with MLflow URI pre-configured
5. **Track**: MLflow automatically captures metrics, params, model
6. **Register**: Model registered to MLflow registry
7. **Serve**: Model available for inference

---

## 📡 API Endpoints

### 1. Upload Training Script

**Endpoint**: `POST /mlops/training/upload`

**Request:**

```json
{
  "script_name": "my_training_script",
  "script_content": "aW1wb3J0IG1sZmxvdw==", // base64 encoded
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "requirements": ["scikit-learn", "pandas", "numpy"],
  "environment_vars": {
    "DATA_PATH": "/data/customers.csv",
    "N_ESTIMATORS": "100"
  },
  "timeout": 300,
  "tags": {
    "team": "data-science",
    "version": "1.0"
  }
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "a1b2c3d4",
  "script_name": "my_training_script",
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "status": "queued",
  "created_at": "2025-10-23T10:00:00Z"
}
```

### 2. Check Job Status

**Endpoint**: `GET /mlops/training/jobs/{job_id}`

**Response:**

```json
{
  "job_id": "a1b2c3d4",
  "script_name": "my_training_script",
  "experiment_name": "customer_churn",
  "model_name": "churn_predictor",
  "status": "completed",
  "run_id": "xyz789abc",
  "model_version": "1",
  "logs": "Training logs...\n✅ Model trained successfully!",
  "error": null,
  "created_at": "2025-10-23T10:00:00Z",
  "started_at": "2025-10-23T10:00:05Z",
  "completed_at": "2025-10-23T10:02:30Z",
  "duration_seconds": 145.2
}
```

**Status Values**:

- `queued` - Job waiting to start
- `running` - Script currently executing
- `completed` - Training finished successfully
- `failed` - Execution failed (see `error` field)

### 3. Model Inference

**Endpoint**: `POST /mlops/inference`

**Request:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "inputs": {
    "total_orders": [10, 25, 5],
    "avg_order_value": [50.0, 120.5, 30.0],
    "days_since_last_order": [5, 15, 30]
  },
  "return_probabilities": true
}
```

**Response:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "predictions": [0, 0, 1],
  "probabilities": [
    [0.9, 0.1],
    [0.85, 0.15],
    [0.3, 0.7]
  ],
  "inference_time_ms": 12.5,
  "timestamp": "2025-10-23T10:05:00Z"
}
```

---

## 📝 Training Script Requirements

### Minimal Example

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

# Generate data
X, y = make_classification(n_samples=1000, n_features=20, random_state=42)

# REQUIRED: Use MLflow run context
with mlflow.start_run():
    # Train model
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    # Log metrics
    mlflow.log_metric("accuracy", model.score(X, y))

    # REQUIRED: Log the model
    mlflow.sklearn.log_model(model, "model")
```

### Required Elements

1. **Import MLflow**: `import mlflow`
2. **Use run context**: `with mlflow.start_run():`
3. **Log model**: `mlflow.<framework>.log_model(model, "model")`

### Best Practices

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score

# Load data (can use environment variables)
import os
data_path = os.getenv("DATA_PATH", "default.csv")

# Start MLflow run
with mlflow.start_run():
    # Log hyperparameters
    params = {"n_estimators": 100, "max_depth": 10}
    mlflow.log_params(params)

    # Train model
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    # Calculate metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("precision", precision)

    # Log model with signature
    mlflow.sklearn.log_model(
        model,
        "model",
        input_example=X_train[:5],
        signature=mlflow.models.infer_signature(X_train, y_pred)
    )

    # Add tags
    mlflow.set_tag("framework", "sklearn")
    mlflow.set_tag("model_type", "RandomForest")
```

---

## 🚀 Quick Start

### Step 1: Create Training Script

```python
# my_model.py
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris

# Load data
X, y = load_iris(return_X_y=True)

# Train
with mlflow.start_run():
    model = LogisticRegression()
    model.fit(X, y)

    mlflow.log_metric("accuracy", model.score(X, y))
    mlflow.sklearn.log_model(model, "model")
```

### Step 2: Upload Script

```bash
# Using the helper utility
python examples/upload_training_script.py \
    --script my_model.py \
    --experiment my_experiment \
    --model my_model \
    --requirements scikit-learn

# Or manually with curl
SCRIPT_B64=$(base64 -w 0 my_model.py)

curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "my_model",
    "script_content": "'$SCRIPT_B64'",
    "experiment_name": "my_experiment",
    "model_name": "my_model",
    "requirements": ["scikit-learn"]
  }'
```

### Step 3: Check Status

```bash
# Poll until completed
JOB_ID="a1b2c3d4"
curl http://localhost:8000/mlops/training/jobs/$JOB_ID
```

### Step 4: Run Inference

```bash
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "my_model",
    "model_version": "1",
    "inputs": {
      "sepal_length": [5.1, 6.2],
      "sepal_width": [3.5, 2.8],
      "petal_length": [1.4, 4.8],
      "petal_width": [0.2, 1.8]
    }
  }'
```

---

## 📚 Example Scripts

The platform includes three complete example scripts:

### 1. Sklearn Classification

**File**: `examples/training_scripts/sklearn_classification.py`

- Random Forest classifier
- Synthetic dataset generation
- Comprehensive metrics logging
- Feature importance tracking

**Upload**:

```bash
python examples/upload_training_script.py \
    --script examples/training_scripts/sklearn_classification.py \
    --experiment sklearn_examples \
    --model rf_classifier \
    --requirements scikit-learn pandas numpy
```

### 2. XGBoost Regression

**File**: `examples/training_scripts/xgboost_regression.py`

- XGBoost regressor
- Early stopping
- Custom evaluation metrics
- RMSE, MAE, R² tracking

**Upload**:

```bash
python examples/upload_training_script.py \
    --script examples/training_scripts/xgboost_regression.py \
    --experiment xgboost_examples \
    --model xgb_regressor \
    --requirements xgboost scikit-learn numpy
```

### 3. LightGBM Classification

**File**: `examples/training_scripts/lightgbm_classification.py`

- LightGBM classifier
- Environment variable configuration
- Feature importance logging
- AUC-ROC tracking

**Upload**:

```bash
python examples/upload_training_script.py \
    --script examples/training_scripts/lightgbm_classification.py \
    --experiment lightgbm_examples \
    --model lgbm_classifier \
    --requirements lightgbm scikit-learn pandas matplotlib \
    --env N_SAMPLES=5000 \
    --env N_FEATURES=25
```

---

## 🔧 Advanced Usage

### Using Environment Variables

```python
# In your script
import os

# Read from environment
n_estimators = int(os.getenv("N_ESTIMATORS", "100"))
data_path = os.getenv("DATA_PATH", "/data/train.csv")

model = RandomForestClassifier(n_estimators=n_estimators)
```

```bash
# Upload with env vars
python upload_training_script.py \
    --script my_script.py \
    --env N_ESTIMATORS=200 \
    --env DATA_PATH=/data/custom.csv \
    ...
```

### Custom Dependencies

```bash
# Upload with specific package versions
python upload_training_script.py \
    --script my_script.py \
    --requirements scikit-learn==1.3.0 pandas==2.0.0 xgboost \
    ...
```

### Longer Training Jobs

```bash
# Increase timeout for long-running jobs
python upload_training_script.py \
    --script long_training.py \
    --timeout 1800  # 30 minutes
    ...
```

---

## 🔍 Troubleshooting

### Issue: Script fails with "No MLflow run created"

**Cause**: Script didn't use `mlflow.start_run()`

**Solution**: Wrap training code in MLflow context:

```python
with mlflow.start_run():
    # All training code here
```

### Issue: Model not available for inference

**Cause**: Model wasn't logged properly

**Solution**: Ensure you call the appropriate log_model:

```python
mlflow.sklearn.log_model(model, "model")      # sklearn
mlflow.xgboost.log_model(model, "model")      # xgboost
mlflow.lightgbm.log_model(model, "model")     # lightgbm
```

### Issue: Execution timeout

**Cause**: Script takes longer than default 300s

**Solution**: Increase timeout:

```bash
--timeout 600  # 10 minutes
```

### Issue: Import errors

**Cause**: Required packages not installed

**Solution**: Add to requirements list:

```bash
--requirements scikit-learn pandas numpy your-package
```

### Issue: Can't read logs

**Cause**: Job still running

**Solution**: Wait for completion or check status:

```bash
curl http://localhost:8000/mlops/training/jobs/$JOB_ID | jq '.logs'
```

---

## 📊 Comparison: Direct API vs Script Upload

| Feature                 | Direct API (`/mlops/models`) | Script Upload (`/mlops/training/upload`) |
| ----------------------- | ---------------------------- | ---------------------------------------- |
| **Flexibility**         | Fixed to Feast features      | Any Python code                          |
| **Data Source**         | Feast only                   | Any source (files, DBs, APIs)            |
| **Frameworks**          | sklearn, xgboost, lightgbm   | Any framework                            |
| **Preprocessing**       | Limited                      | Full control                             |
| **Feature Engineering** | Feast-based                  | Custom code                              |
| **Use Case**            | Standardized ML pipeline     | Custom/experimental models               |

---

## 🎯 Best Practices

1. **Always test scripts locally first** with MLflow tracking
2. **Use environment variables** for configuration
3. **Log comprehensive metrics** for model comparison
4. **Include input examples** in log_model calls
5. **Set appropriate timeouts** based on data size
6. **Use version tags** to track model iterations
7. **Monitor job status** and handle failures gracefully

---

## 📖 Additional Resources

- **Example Scripts**: `/examples/training_scripts/`
- **Upload Utility**: `/examples/upload_training_script.py`
- **MLflow Docs**: https://mlflow.org/docs/latest/
- **API Documentation**: http://localhost:8000/docs

---

## ✅ Summary

The script-based training feature enables:

- ✅ Upload any Python training code
- ✅ Automatic MLflow integration
- ✅ Custom dependencies and environment
- ✅ Job tracking and logging
- ✅ Model inference via REST API

**Perfect for**: Custom models, experimental algorithms, special preprocessing, non-Feast data sources

---

**Date**: October 23, 2025  
**Feature Status**: ✅ Production Ready  
**Documentation Version**: 4.0.0
