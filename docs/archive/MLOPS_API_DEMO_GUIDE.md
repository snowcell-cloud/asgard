# MLOps Platform API - Complete Demo Guide

**Purpose:** Client demonstration of complete MLOps lifecycle with MLflow and Feast  
**Date:** November 4, 2025  
**Status:** Production Ready ✅

---

## 📋 Table of Contents

1. [Quick Setup](#quick-setup)
2. [API Endpoint Overview](#api-endpoint-overview)
3. [Demo Scenario 1: Customer Churn Prediction](#demo-scenario-1-customer-churn-prediction)
4. [Demo Scenario 2: Product Recommendation Model](#demo-scenario-2-product-recommendation-model)
5. [Demo Scenario 3: Fraud Detection System](#demo-scenario-3-fraud-detection-system)
6. [Complete cURL Examples](#complete-curl-examples)
7. [Python Client Examples](#python-client-examples)
8. [Postman Collection](#postman-collection)
9. [Training Script Templates](#training-script-templates)

---

## Quick Setup

### Port Forward Services

```bash
# Forward Asgard MLOps API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# Forward MLflow UI (optional)
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# Verify connectivity
curl http://localhost:8000/mlops/status
```

### Expected Response

```json
{
  "mlflow_tracking_uri": "http://mlflow-service:5000",
  "mlflow_available": true,
  "feast_store_available": true,
  "registered_models": 0,
  "active_experiments": 5,
  "feature_views": 0,
  "timestamp": "2025-11-04T10:00:00"
}
```

### Access Points

- **MLOps API Docs**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000

---

## API Endpoint Overview

| Endpoint | Method | Purpose | Demo Priority |
|----------|--------|---------|---------------|
| `/mlops/status` | GET | Platform health check | ⭐⭐⭐ High |
| `/mlops/training/upload` | POST | Upload & execute training script | ⭐⭐⭐ High |
| `/mlops/training/jobs/{job_id}` | GET | Check training job status | ⭐⭐⭐ High |
| `/mlops/models` | GET | List registered models | ⭐⭐⭐ High |
| `/mlops/models/{model_name}` | GET | Get model details | ⭐⭐ Medium |
| `/mlops/inference` | POST | Run model predictions | ⭐⭐⭐ High |
| `/mlops/registry` | POST | Register model manually | ⭐ Low |

---

## Demo Scenario 1: Customer Churn Prediction

### Use Case
Train a churn prediction model using customer behavioral features from Feast feature store.

### Step 1: Check Platform Status

```bash
curl -X GET http://localhost:8000/mlops/status | jq
```

**Expected Response:**
```json
{
  "mlflow_tracking_uri": "http://mlflow-service:5000",
  "mlflow_available": true,
  "feast_store_available": true,
  "registered_models": 0,
  "active_experiments": 5,
  "feature_views": 0,
  "timestamp": "2025-11-04T10:00:00.123456"
}
```

### Step 2: Create Feast Feature View (Optional)

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_churn_features",
    "entities": ["customer_id"],
    "features": [
      {"name": "total_purchases", "dtype": "int64"},
      {"name": "avg_purchase_value", "dtype": "float64"},
      {"name": "days_since_last_purchase", "dtype": "int32"},
      {"name": "customer_lifetime_value", "dtype": "float64"},
      {"name": "account_age_days", "dtype": "int32"},
      {"name": "support_tickets_count", "dtype": "int32"}
    ],
    "source": {
      "table_name": "customer_metrics",
      "timestamp_field": "updated_at",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 2592000,
    "description": "Customer features for churn prediction"
  }'
```

### Step 3: Prepare Training Script

Create a file `churn_training.py`:

```python
import os
import mlflow
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import tempfile

# Suppress warnings
os.environ['GIT_PYTHON_REFRESH'] = 'quiet'
import logging
logging.getLogger("mlflow").setLevel(logging.ERROR)

# Generate synthetic churn data (in production, use Feast features)
np.random.seed(42)
n_samples = 1000

data = pd.DataFrame({
    'total_purchases': np.random.randint(1, 50, n_samples),
    'avg_purchase_value': np.random.uniform(10, 500, n_samples),
    'days_since_last_purchase': np.random.randint(0, 365, n_samples),
    'customer_lifetime_value': np.random.uniform(100, 10000, n_samples),
    'account_age_days': np.random.randint(30, 1825, n_samples),
    'support_tickets_count': np.random.randint(0, 20, n_samples),
})

# Create target variable (churn)
data['churned'] = (
    (data['days_since_last_purchase'] > 180) & 
    (data['support_tickets_count'] > 5)
).astype(int)

X = data.drop('churned', axis=1)
y = data['churned']

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model with MLflow tracking
with mlflow.start_run() as run:
    # Log parameters
    params = {
        "n_estimators": 100,
        "max_depth": 10,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "random_state": 42,
        "n_samples": n_samples,
        "test_size": 0.2,
        "model_type": "RandomForestClassifier"
    }
    
    for key, value in params.items():
        mlflow.log_param(key, value)
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_split=params["min_samples_split"],
        min_samples_leaf=params["min_samples_leaf"],
        random_state=params["random_state"]
    )
    
    model.fit(X_train, y_train)
    
    # Make predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Calculate metrics
    metrics = {
        "train_accuracy": accuracy_score(y_train, y_pred_train),
        "test_accuracy": accuracy_score(y_test, y_pred_test),
        "train_precision": precision_score(y_train, y_pred_train, zero_division=0),
        "test_precision": precision_score(y_test, y_pred_test, zero_division=0),
        "train_recall": recall_score(y_train, y_pred_train, zero_division=0),
        "test_recall": recall_score(y_test, y_pred_test, zero_division=0),
        "train_f1": f1_score(y_train, y_pred_train, zero_division=0),
        "test_f1": f1_score(y_test, y_pred_test, zero_division=0)
    }
    
    for key, value in metrics.items():
        mlflow.log_metric(key, value)
    
    # Log feature importances
    feature_importance = dict(zip(X.columns, model.feature_importances_))
    for feature, importance in feature_importance.items():
        mlflow.log_metric(f"importance_{feature}", importance)
    
    # Save model as artifact
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        mlflow.log_artifact(model_path, artifact_path="model")
    
    print(f"✅ Training completed successfully!")
    print(f"   Run ID: {run.info.run_id}")
    print(f"   Test Accuracy: {metrics['test_accuracy']:.3f}")
    print(f"   Test F1 Score: {metrics['test_f1']:.3f}")
```

### Step 4: Encode and Upload Training Script

```bash
# Encode the script to base64
SCRIPT_B64=$(base64 -w 0 churn_training.py)

# Upload and execute
curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"script_name\": \"churn_training.py\",
    \"script_content\": \"$SCRIPT_B64\",
    \"experiment_name\": \"customer_churn_prediction\",
    \"model_name\": \"churn_predictor_v1\",
    \"requirements\": [\"scikit-learn\", \"pandas\", \"numpy\"],
    \"environment_vars\": {
      \"USE_FEAST\": \"true\",
      \"FEATURE_VIEW\": \"customer_churn_features\"
    },
    \"timeout\": 600,
    \"tags\": {
      \"version\": \"1.0\",
      \"team\": \"data-science\",
      \"use_case\": \"churn_prediction\"
    }
  }"
```

**Expected Response:**
```json
{
  "job_id": "abc123def456",
  "script_name": "churn_training.py",
  "experiment_name": "customer_churn_prediction",
  "model_name": "churn_predictor_v1",
  "status": "queued",
  "run_id": null,
  "model_version": null,
  "error": null,
  "created_at": "2025-11-04T10:05:00.123456",
  "started_at": null,
  "completed_at": null
}
```

### Step 5: Monitor Training Progress

```bash
# Get job status (replace with actual job_id)
JOB_ID="abc123def456"

curl -X GET "http://localhost:8000/mlops/training/jobs/$JOB_ID" | jq
```

**Expected Response (In Progress):**
```json
{
  "job_id": "abc123def456",
  "script_name": "churn_training.py",
  "experiment_name": "customer_churn_prediction",
  "model_name": "churn_predictor_v1",
  "status": "running",
  "run_id": null,
  "model_version": null,
  "logs": "Starting training...\nLoading data...\n",
  "error": null,
  "created_at": "2025-11-04T10:05:00.123456",
  "started_at": "2025-11-04T10:05:01.234567",
  "completed_at": null,
  "duration_seconds": 15.5
}
```

**Expected Response (Completed):**
```json
{
  "job_id": "abc123def456",
  "script_name": "churn_training.py",
  "experiment_name": "customer_churn_prediction",
  "model_name": "churn_predictor_v1",
  "status": "completed",
  "run_id": "1234567890abcdef",
  "model_version": "1",
  "logs": "✅ Training completed successfully!\n   Run ID: 1234567890abcdef\n   Test Accuracy: 0.985\n   Test F1 Score: 0.975",
  "error": null,
  "created_at": "2025-11-04T10:05:00.123456",
  "started_at": "2025-11-04T10:05:01.234567",
  "completed_at": "2025-11-04T10:05:45.678901",
  "duration_seconds": 44.444334
}
```

### Step 6: List Registered Models

```bash
curl -X GET http://localhost:8000/mlops/models | jq
```

**Expected Response:**
```json
[
  {
    "name": "churn_predictor_v1",
    "description": null,
    "tags": {},
    "latest_versions": [
      {
        "name": "churn_predictor_v1",
        "version": "1",
        "stage": "None",
        "run_id": "1234567890abcdef",
        "description": null,
        "tags": {
          "version": "1.0",
          "team": "data-science",
          "use_case": "churn_prediction"
        },
        "created_at": "2025-11-04T10:05:45.678901",
        "updated_at": "2025-11-04T10:05:45.678901"
      }
    ],
    "created_at": "2025-11-04T10:05:45.678901",
    "updated_at": "2025-11-04T10:05:45.678901"
  }
]
```

### Step 7: Get Specific Model Details

```bash
curl -X GET http://localhost:8000/mlops/models/churn_predictor_v1 | jq
```

### Step 8: Run Inference

```bash
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "churn_predictor_v1",
    "model_version": "1",
    "inputs": {
      "total_purchases": [10, 25, 5, 40],
      "avg_purchase_value": [50.0, 120.5, 30.0, 200.0],
      "days_since_last_purchase": [5, 15, 200, 10],
      "customer_lifetime_value": [500.0, 3000.0, 150.0, 8000.0],
      "account_age_days": [365, 730, 180, 1095],
      "support_tickets_count": [2, 1, 8, 0]
    },
    "return_probabilities": true
  }'
```

**Expected Response:**
```json
{
  "model_name": "churn_predictor_v1",
  "model_version": "1",
  "predictions": [0, 0, 1, 0],
  "probabilities": [
    [0.92, 0.08],
    [0.88, 0.12],
    [0.15, 0.85],
    [0.95, 0.05]
  ],
  "inference_time_ms": 8.5,
  "timestamp": "2025-11-04T10:10:00.123456"
}
```

**Interpretation:**
- Customer 1: 8% churn probability (low risk)
- Customer 2: 12% churn probability (low risk)
- Customer 3: 85% churn probability (high risk - needs intervention!)
- Customer 4: 5% churn probability (low risk)

---

## Demo Scenario 2: Product Recommendation Model

### Use Case
Train a collaborative filtering model for product recommendations.

### Training Script: `recommendation_training.py`

```python
import os
import mlflow
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import pickle
import tempfile

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

# Generate synthetic product interaction data
np.random.seed(42)
n_products = 500

product_data = pd.DataFrame({
    'view_count_7d': np.random.randint(0, 10000, n_products),
    'purchase_count_7d': np.random.randint(0, 500, n_products),
    'add_to_cart_count_7d': np.random.randint(0, 1000, n_products),
    'avg_rating': np.random.uniform(1, 5, n_products),
    'price': np.random.uniform(10, 1000, n_products),
    'discount_percentage': np.random.uniform(0, 50, n_products),
})

with mlflow.start_run() as run:
    # Log parameters
    params = {
        "n_neighbors": 10,
        "algorithm": "ball_tree",
        "metric": "euclidean",
        "n_products": n_products
    }
    
    for key, value in params.items():
        mlflow.log_param(key, value)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(product_data)
    
    # Train KNN model
    model = NearestNeighbors(
        n_neighbors=params["n_neighbors"],
        algorithm=params["algorithm"],
        metric=params["metric"]
    )
    
    model.fit(X_scaled)
    
    # Log metrics
    mlflow.log_metric("total_products", n_products)
    mlflow.log_metric("avg_views", product_data['view_count_7d'].mean())
    mlflow.log_metric("avg_rating", product_data['avg_rating'].mean())
    
    # Save model and scaler
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        scaler_path = os.path.join(tmpdir, "scaler.pkl")
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        mlflow.log_artifact(model_path, artifact_path="model")
        mlflow.log_artifact(scaler_path, artifact_path="model")
    
    print(f"✅ Recommendation model training completed!")
    print(f"   Run ID: {run.info.run_id}")
    print(f"   Products: {n_products}")
```

### Upload Command

```bash
SCRIPT_B64=$(base64 -w 0 recommendation_training.py)

curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"script_name\": \"recommendation_training.py\",
    \"script_content\": \"$SCRIPT_B64\",
    \"experiment_name\": \"product_recommendations\",
    \"model_name\": \"product_recommender_knn\",
    \"requirements\": [\"scikit-learn\", \"pandas\", \"numpy\"],
    \"timeout\": 300,
    \"tags\": {
      \"version\": \"1.0\",
      \"team\": \"ml-platform\",
      \"model_type\": \"knn\"
    }
  }"
```

---

## Demo Scenario 3: Fraud Detection System

### Use Case
Real-time fraud detection using transaction patterns.

### Training Script: `fraud_detection_training.py`

```python
import os
import mlflow
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
import tempfile

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

# Generate synthetic transaction data
np.random.seed(42)
n_transactions = 10000

# Normal transactions
normal = pd.DataFrame({
    'amount': np.random.uniform(10, 500, int(n_transactions * 0.95)),
    'transaction_count_24h': np.random.randint(1, 10, int(n_transactions * 0.95)),
    'avg_transaction_amount': np.random.uniform(20, 400, int(n_transactions * 0.95)),
    'unique_merchants_24h': np.random.randint(1, 8, int(n_transactions * 0.95)),
})

# Fraudulent transactions (outliers)
fraud = pd.DataFrame({
    'amount': np.random.uniform(1000, 10000, int(n_transactions * 0.05)),
    'transaction_count_24h': np.random.randint(20, 100, int(n_transactions * 0.05)),
    'avg_transaction_amount': np.random.uniform(500, 5000, int(n_transactions * 0.05)),
    'unique_merchants_24h': np.random.randint(15, 50, int(n_transactions * 0.05)),
})

data = pd.concat([normal, fraud], ignore_index=True)

with mlflow.start_run() as run:
    # Log parameters
    params = {
        "contamination": 0.05,
        "n_estimators": 100,
        "max_samples": 256,
        "random_state": 42,
        "n_transactions": n_transactions
    }
    
    for key, value in params.items():
        mlflow.log_param(key, value)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data)
    
    # Train Isolation Forest
    model = IsolationForest(
        contamination=params["contamination"],
        n_estimators=params["n_estimators"],
        max_samples=params["max_samples"],
        random_state=params["random_state"]
    )
    
    model.fit(X_scaled)
    
    # Predict (1 = normal, -1 = fraud)
    predictions = model.predict(X_scaled)
    anomaly_score = model.score_samples(X_scaled)
    
    # Log metrics
    fraud_detected = (predictions == -1).sum()
    mlflow.log_metric("total_transactions", n_transactions)
    mlflow.log_metric("fraud_detected", fraud_detected)
    mlflow.log_metric("fraud_percentage", (fraud_detected / n_transactions) * 100)
    mlflow.log_metric("avg_anomaly_score", anomaly_score.mean())
    
    # Save model and scaler
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        scaler_path = os.path.join(tmpdir, "scaler.pkl")
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        mlflow.log_artifact(model_path, artifact_path="model")
        mlflow.log_artifact(scaler_path, artifact_path="model")
    
    print(f"✅ Fraud detection model trained!")
    print(f"   Run ID: {run.info.run_id}")
    print(f"   Fraud detected: {fraud_detected} ({fraud_detected/n_transactions*100:.2f}%)")
```

---

## Complete cURL Examples

### 1. Check Platform Status

```bash
curl -X GET http://localhost:8000/mlops/status \
  -H "Accept: application/json" | jq
```

### 2. Upload Training Script (Simple)

```bash
# Create simple script
cat > simple_model.py << 'EOF'
import mlflow
import pickle
import tempfile
import os

with mlflow.start_run() as run:
    mlflow.log_param("model_type", "simple")
    mlflow.log_metric("accuracy", 0.95)
    
    # Save dummy model
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump({"dummy": "model"}, f)
        mlflow.log_artifact(model_path, artifact_path="model")
    
    print(f"Run ID: {run.info.run_id}")
EOF

# Encode and upload
SCRIPT_B64=$(base64 -w 0 simple_model.py)

curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"script_name\": \"simple_model.py\",
    \"script_content\": \"$SCRIPT_B64\",
    \"experiment_name\": \"simple_test\",
    \"model_name\": \"simple_model\",
    \"requirements\": [],
    \"timeout\": 120
  }"
```

### 3. Check Job Status

```bash
# Replace JOB_ID with actual value from upload response
JOB_ID="your-job-id-here"

curl -X GET "http://localhost:8000/mlops/training/jobs/$JOB_ID" \
  -H "Accept: application/json" | jq
```

### 4. List All Models

```bash
curl -X GET http://localhost:8000/mlops/models \
  -H "Accept: application/json" | jq
```

### 5. Get Model Details

```bash
MODEL_NAME="churn_predictor_v1"

curl -X GET "http://localhost:8000/mlops/models/$MODEL_NAME" \
  -H "Accept: application/json" | jq
```

### 6. Run Inference (Classification)

```bash
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "churn_predictor_v1",
    "model_version": "1",
    "inputs": {
      "total_purchases": [10, 25, 5],
      "avg_purchase_value": [50.0, 120.5, 30.0],
      "days_since_last_purchase": [5, 15, 200],
      "customer_lifetime_value": [500.0, 3000.0, 150.0],
      "account_age_days": [365, 730, 180],
      "support_tickets_count": [2, 1, 8]
    },
    "return_probabilities": true
  }' | jq
```

### 7. Register Model Manually (Advanced)

```bash
curl -X POST http://localhost:8000/mlops/registry \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "my_custom_model",
    "run_id": "1234567890abcdef",
    "description": "Manually registered model from specific run",
    "tags": {
      "version": "2.0",
      "trained_by": "john.doe"
    }
  }' | jq
```

---

## Python Client Examples

### Complete MLOps Client

```python
import requests
import base64
import time
import json
from typing import Dict, List, Any, Optional

class MLOpsClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.mlops_url = f"{base_url}/mlops"
    
    def get_status(self) -> Dict:
        """Get MLOps platform status."""
        response = requests.get(f"{self.mlops_url}/status")
        response.raise_for_status()
        return response.json()
    
    def upload_script(
        self,
        script_path: str,
        experiment_name: str,
        model_name: str,
        requirements: List[str] = None,
        env_vars: Dict[str, str] = None,
        timeout: int = 600,
        tags: Dict[str, str] = None
    ) -> Dict:
        """Upload and execute training script."""
        with open(script_path, "rb") as f:
            script_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            "script_name": script_path.split('/')[-1],
            "script_content": script_b64,
            "experiment_name": experiment_name,
            "model_name": model_name,
            "requirements": requirements or [],
            "environment_vars": env_vars or {},
            "timeout": timeout,
            "tags": tags or {}
        }
        
        response = requests.post(
            f"{self.mlops_url}/training/upload",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get training job status."""
        response = requests.get(f"{self.mlops_url}/training/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_job(
        self,
        job_id: str,
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Dict:
        """Wait for training job to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status['status'] in ['completed', 'failed']:
                return status
            
            print(f"Status: {status['status']} (elapsed: {status.get('duration_seconds', 0):.1f}s)")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
    
    def list_models(self) -> List[Dict]:
        """List all registered models."""
        response = requests.get(f"{self.mlops_url}/models")
        response.raise_for_status()
        return response.json()
    
    def get_model(self, model_name: str) -> Dict:
        """Get specific model details."""
        response = requests.get(f"{self.mlops_url}/models/{model_name}")
        response.raise_for_status()
        return response.json()
    
    def inference(
        self,
        model_name: str,
        inputs: Dict[str, List[Any]],
        model_version: Optional[str] = None,
        return_probabilities: bool = False
    ) -> Dict:
        """Run model inference."""
        payload = {
            "model_name": model_name,
            "inputs": inputs,
            "return_probabilities": return_probabilities
        }
        
        if model_version:
            payload["model_version"] = model_version
        
        response = requests.post(
            f"{self.mlops_url}/inference",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def register_model(
        self,
        model_name: str,
        run_id: str,
        description: Optional[str] = None,
        tags: Dict[str, str] = None
    ) -> Dict:
        """Manually register a model."""
        payload = {
            "model_name": model_name,
            "run_id": run_id,
            "description": description,
            "tags": tags or {}
        }
        
        response = requests.post(
            f"{self.mlops_url}/registry",
            json=payload
        )
        response.raise_for_status()
        return response.json()
```

### Example Usage

```python
#!/usr/bin/env python3
"""
MLOps API Demo Script
End-to-end demonstration of model training and inference.
"""

from mlops_client import MLOpsClient

def main():
    client = MLOpsClient()
    
    print("=" * 70)
    print("MLOPS PLATFORM DEMO - CUSTOMER CHURN PREDICTION")
    print("=" * 70)
    
    # Step 1: Check status
    print("\n1️⃣  Checking Platform Status...")
    status = client.get_status()
    print(f"   ✓ MLflow available: {status['mlflow_available']}")
    print(f"   ✓ Feast available: {status['feast_store_available']}")
    print(f"   ✓ Active experiments: {status['active_experiments']}")
    
    # Step 2: Upload training script
    print("\n2️⃣  Uploading Training Script...")
    job = client.upload_script(
        script_path="churn_training.py",
        experiment_name="customer_churn_demo",
        model_name="churn_predictor_demo",
        requirements=["scikit-learn", "pandas", "numpy"],
        timeout=600,
        tags={"demo": "true", "version": "1.0"}
    )
    print(f"   ✓ Job ID: {job['job_id']}")
    print(f"   ✓ Status: {job['status']}")
    
    # Step 3: Wait for training to complete
    print("\n3️⃣  Waiting for Training to Complete...")
    result = client.wait_for_job(job['job_id'], timeout=600)
    
    if result['status'] == 'completed':
        print(f"   ✅ Training completed!")
        print(f"   ✓ Run ID: {result['run_id']}")
        print(f"   ✓ Model version: {result['model_version']}")
        print(f"   ✓ Duration: {result['duration_seconds']:.2f}s")
    else:
        print(f"   ❌ Training failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        return
    
    # Step 4: List models
    print("\n4️⃣  Listing Registered Models...")
    models = client.list_models()
    for model in models:
        print(f"   - {model['name']}")
        for version in model['latest_versions']:
            print(f"     Version {version['version']} (stage: {version['stage']})")
    
    # Step 5: Run inference
    print("\n5️⃣  Running Inference...")
    predictions = client.inference(
        model_name="churn_predictor_demo",
        model_version="1",
        inputs={
            "total_purchases": [10, 25, 5, 40],
            "avg_purchase_value": [50.0, 120.5, 30.0, 200.0],
            "days_since_last_purchase": [5, 15, 200, 10],
            "customer_lifetime_value": [500.0, 3000.0, 150.0, 8000.0],
            "account_age_days": [365, 730, 180, 1095],
            "support_tickets_count": [2, 1, 8, 0]
        },
        return_probabilities=True
    )
    
    print(f"   ✓ Inference time: {predictions['inference_time_ms']:.2f}ms")
    print(f"   ✓ Predictions: {predictions['predictions']}")
    
    print("\n   Customer Churn Risk Analysis:")
    for i, (pred, prob) in enumerate(zip(
        predictions['predictions'],
        predictions['probabilities']
    ), 1):
        risk = "HIGH" if pred == 1 else "LOW"
        confidence = prob[1] if pred == 1 else prob[0]
        print(f"   Customer {i}: {risk} risk ({confidence*100:.1f}% confidence)")
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
```

---

## Postman Collection

### Import Instructions

1. Open Postman
2. Click **Import**
3. Paste the JSON below
4. Update `{{baseUrl}}` variable to `http://localhost:8000`

### Collection JSON

```json
{
  "info": {
    "name": "MLOps Platform API - Complete Demo",
    "description": "Complete MLOps lifecycle demonstration",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "jobId",
      "value": "",
      "type": "string"
    },
    {
      "key": "modelName",
      "value": "churn_predictor_v1",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "1. Platform Status",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/mlops/status",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "status"]
        }
      }
    },
    {
      "name": "2. Upload Training Script",
      "event": [
        {
          "listen": "test",
          "script": {
            "exec": [
              "const response = pm.response.json();",
              "pm.environment.set('jobId', response.job_id);"
            ],
            "type": "text/javascript"
          }
        }
      ],
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"script_name\": \"churn_training.py\",\n  \"script_content\": \"aW1wb3J0IG1sZmxvdwppbXBvcnQgcGlja2xlCmltcG9ydCB0ZW1wZmlsZQppbXBvcnQgb3MKCndpdGggbWxmbG93LnN0YXJ0X3J1bigpIGFzIHJ1bjoKICAgIG1sZmxvdy5sb2dfcGFyYW0oIm1vZGVsX3R5cGUiLCAic2ltcGxlIikKICAgIG1sZmxvdy5sb2dfbWV0cmljKCJhY2N1cmFjeSIsIDAuOTUpCiAgICAKICAgIHdpdGggdGVtcGZpbGUuVGVtcG9yYXJ5RGlyZWN0b3J5KCkgYXMgdG1wZGlyOgogICAgICAgIG1vZGVsX3BhdGggPSBvcy5wYXRoLmpvaW4odG1wZGlyLCAibW9kZWwucGtsIikKICAgICAgICB3aXRoIG9wZW4obW9kZWxfcGF0aCwgJ3diJykgYXMgZjoKICAgICAgICAgICAgcGlja2xlLmR1bXAoeyJkdW1teSI6ICJtb2RlbCJ9LCBmKQogICAgICAgIG1sZmxvdy5sb2dfYXJ0aWZhY3QobW9kZWxfcGF0aCwgYXJ0aWZhY3RfcGF0aD0ibW9kZWwiKQogICAgCiAgICBwcmludChmIlJ1biBJRDoge3J1bi5pbmZvLnJ1bl9pZH0iKQ==\",\n  \"experiment_name\": \"demo_experiment\",\n  \"model_name\": \"demo_model\",\n  \"requirements\": [],\n  \"timeout\": 300,\n  \"tags\": {\n    \"demo\": \"true\"\n  }\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/mlops/training/upload",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "training", "upload"]
        }
      }
    },
    {
      "name": "3. Check Job Status",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/mlops/training/jobs/{{jobId}}",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "training", "jobs", "{{jobId}}"]
        }
      }
    },
    {
      "name": "4. List All Models",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/mlops/models",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "models"]
        }
      }
    },
    {
      "name": "5. Get Model Details",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/mlops/models/{{modelName}}",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "models", "{{modelName}}"]
        }
      }
    },
    {
      "name": "6. Run Inference",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"model_name\": \"{{modelName}}\",\n  \"model_version\": \"1\",\n  \"inputs\": {\n    \"total_purchases\": [10, 25, 5],\n    \"avg_purchase_value\": [50.0, 120.5, 30.0],\n    \"days_since_last_purchase\": [5, 15, 200],\n    \"customer_lifetime_value\": [500.0, 3000.0, 150.0],\n    \"account_age_days\": [365, 730, 180],\n    \"support_tickets_count\": [2, 1, 8]\n  },\n  \"return_probabilities\": true\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/mlops/inference",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "inference"]
        }
      }
    },
    {
      "name": "7. Register Model Manually",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"model_name\": \"custom_model\",\n  \"run_id\": \"replace-with-actual-run-id\",\n  \"description\": \"Manually registered model\",\n  \"tags\": {\n    \"version\": \"1.0\"\n  }\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/mlops/registry",
          "host": ["{{baseUrl}}"],
          "path": ["mlops", "registry"]
        }
      }
    }
  ]
}
```

---

## Training Script Templates

### Template 1: Classification Model

```python
import os
import mlflow
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import pickle
import tempfile

# Suppress warnings
os.environ['GIT_PYTHON_REFRESH'] = 'quiet'
import logging
logging.getLogger("mlflow").setLevel(logging.ERROR)

# Load your data here
# In production, load from Feast feature store
data = pd.read_csv('/path/to/data.csv')  # Replace with actual path

X = data.drop('target', axis=1)
y = data['target']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

with mlflow.start_run() as run:
    # Parameters
    params = {
        "n_estimators": 100,
        "max_depth": 10,
        "random_state": 42
    }
    
    for key, value in params.items():
        mlflow.log_param(key, value)
    
    # Train
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)
    
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    mlflow.log_metric("accuracy", accuracy_score(y_test, y_pred))
    mlflow.log_metric("precision", precision_score(y_test, y_pred))
    mlflow.log_metric("recall", recall_score(y_test, y_pred))
    mlflow.log_metric("f1_score", f1_score(y_test, y_pred))
    mlflow.log_metric("roc_auc", roc_auc_score(y_test, y_proba))
    
    # Save model
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        mlflow.log_artifact(model_path, artifact_path="model")
    
    print(f"✅ Training completed! Run ID: {run.info.run_id}")
```

### Template 2: Regression Model

```python
import os
import mlflow
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import pickle
import tempfile
import numpy as np

os.environ['GIT_PYTHON_REFRESH'] = 'quiet'

data = pd.read_csv('/path/to/data.csv')

X = data.drop('target', axis=1)
y = data['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

with mlflow.start_run() as run:
    params = {"alpha": 1.0, "random_state": 42}
    
    for key, value in params.items():
        mlflow.log_param(key, value)
    
    model = Ridge(**params)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    
    mlflow.log_metric("mse", mean_squared_error(y_test, y_pred))
    mlflow.log_metric("rmse", np.sqrt(mean_squared_error(y_test, y_pred)))
    mlflow.log_metric("mae", mean_absolute_error(y_test, y_pred))
    mlflow.log_metric("r2", r2_score(y_test, y_pred))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = os.path.join(tmpdir, "model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        mlflow.log_artifact(model_path, artifact_path="model")
    
    print(f"✅ Regression model trained! Run ID: {run.info.run_id}")
```

---

## Demo Presentation Flow

### For Client Meeting (20 minutes)

**Slide 1: Platform Overview (2 min)**
- Show architecture: Feast → MLOps → MLflow
- Explain end-to-end ML lifecycle

**Slide 2: Check Status (1 min)**
```bash
curl http://localhost:8000/mlops/status | jq
```

**Slide 3: Upload Training Script (3 min)**
- Show churn prediction use case
- Explain script requirements
- POST /mlops/training/upload

**Slide 4: Monitor Training (3 min)**
- GET /mlops/training/jobs/{job_id}
- Show status transitions: queued → running → completed
- Display logs and run_id

**Slide 5: View in MLflow UI (2 min)**
- Open http://localhost:5000
- Show experiment, metrics, parameters
- View model artifacts

**Slide 6: List Models (2 min)**
```bash
curl http://localhost:8000/mlops/models | jq
```
- Show registered models
- Version information

**Slide 7: Run Inference (4 min)**
- POST /mlops/inference
- Show predictions and probabilities
- Explain business interpretation

**Slide 8: Production Features (2 min)**
- Feast integration
- S3 artifact storage
- Kubernetes deployment

**Slide 9: Next Steps (1 min)**
- Additional models
- A/B testing
- Model monitoring

---

## Key Demo Talking Points

### Technical Highlights

✅ **Script-based Training** - Upload any Python ML script  
✅ **Automatic Tracking** - MLflow logs everything automatically  
✅ **Model Registry** - Versioned model storage  
✅ **Background Execution** - Async training with status monitoring  
✅ **Feast Integration** - Feature store for consistent features  
✅ **S3 Artifacts** - Scalable model artifact storage  
✅ **Production Ready** - Kubernetes-native deployment

### Business Value

💰 **Faster Time to Market** - Deploy models in minutes, not days  
⚡ **Reproducibility** - Every training run is tracked and versioned  
🔒 **Governance** - Complete audit trail of models  
📊 **Experimentation** - Easy A/B testing of model versions  
🎯 **Consistency** - Same features for training and serving  
💪 **Scalability** - Cloud-native architecture

---

## Troubleshooting

### Issue: Training Stuck in "queued"

**Solution:** Check pod logs
```bash
kubectl logs -n asgard -l app=asgard-app --tail=100
```

### Issue: Model Artifacts Not Saved

**Solution:** Verify AWS credentials
```bash
kubectl exec -n asgard <pod-name> -- env | grep AWS
```

### Issue: Inference Returns Error

**Solution:** Ensure input features match training data
```bash
# Check model metadata in MLflow UI
http://localhost:5000
```

---

## Summary

This demo guide provides **complete, production-ready examples** for demonstrating the full MLOps platform to clients:

- ✅ 3 realistic business scenarios (churn, recommendations, fraud)
- ✅ All 7 API endpoints covered
- ✅ Complete request/response examples
- ✅ cURL commands for live demos
- ✅ Python client for automation
- ✅ Postman collection for GUI testing
- ✅ Training script templates
- ✅ 20-minute presentation flow

**Status: Production Ready** 🚀

---

**Last Updated:** November 4, 2025  
**Author:** Asgard Platform Team  
**MLflow UI:** http://localhost:5000  
**API Docs:** http://localhost:8000/docs
