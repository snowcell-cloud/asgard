# ✨ Single-Click ML Deployment - Complete Guide

**Date**: November 13, 2025  
**Feature**: Synchronous deployment with immediate inference URL

---

## 🎯 Overview

**Deploy a trained ML model in ONE API call and get the inference URL immediately!**

No more polling, no more waiting for status - just one request, one response with everything you need.

---

## 🚀 Single API Call

### `POST /mlops/deploy`

**What it does:**

1. ✅ Trains your model
2. ✅ Builds Docker image
3. ✅ Pushes to ECR
4. ✅ Deploys to Kubernetes
5. ✅ Waits for LoadBalancer IP
6. ✅ **Returns inference URL in response**

**Duration**: ~3-5 minutes (synchronous)

---

## 📝 Complete Example

### Request

```bash
curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train_model.py",
    "script_content": "import mlflow\nimport pandas as pd\nfrom sklearn.ensemble import RandomForestClassifier\n\ndata = pd.DataFrame({\"f1\": [1,2,3,4,5], \"f2\": [2,4,6,8,10], \"target\": [0,0,1,1,0]})\nX = data[[\"f1\", \"f2\"]]\ny = data[\"target\"]\n\nwith mlflow.start_run():\n    model = RandomForestClassifier(n_estimators=10)\n    model.fit(X, y)\n    mlflow.sklearn.log_model(model, \"model\")\n    mlflow.log_metric(\"accuracy\", 0.95)\n    print(\"Model trained successfully!\")",
    "experiment_name": "production_experiment",
    "model_name": "churn_predictor",
    "requirements": ["scikit-learn==1.3.2", "pandas==2.1.3"],
    "replicas": 2,
    "namespace": "asgard"
  }'
```

### Response (After ~3-5 minutes)

```json
{
  "model_name": "churn_predictor",
  "experiment_name": "production_experiment",
  "status": "deployed",
  "inference_url": "http://51.89.136.142",
  "external_ip": "51.89.136.142",
  "model_version": "1",
  "run_id": "7da8457f3fa04a6189fb3fce7ebb0259",
  "ecr_image": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model:churn-predictor-v1",
  "endpoints": {
    "health": "http://51.89.136.142/health",
    "metadata": "http://51.89.136.142/metadata",
    "predict": "http://51.89.136.142/predict",
    "root": "http://51.89.136.142"
  },
  "deployment_time_seconds": 245.3,
  "message": "Model deployed successfully! Use http://51.89.136.142/predict for inference"
}
```

---

## 🎯 Immediate Next Steps

### 1. Test Health

```bash
INFERENCE_URL="http://51.89.136.142"

curl $INFERENCE_URL/health
```

**Response:**

```json
{
  "status": "healthy",
  "model": {
    "name": "churn_predictor",
    "version": "1",
    "run_id": "7da8457f3fa04a6189fb3fce7ebb0259"
  }
}
```

### 2. Make Predictions

```bash
curl -X POST $INFERENCE_URL/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "f1": [1, 2, 3],
      "f2": [2, 4, 6]
    }
  }'
```

**Response:**

```json
{
  "predictions": [0, 0, 1]
}
```

### 3. Get Metadata

```bash
curl $INFERENCE_URL/metadata
```

**Response:**

```json
{
  "model_name": "churn_predictor",
  "model_version": "1",
  "run_id": "7da8457f3fa04a6189fb3fce7ebb0259",
  "mlflow_uri": "http://mlflow-service.asgard.svc.cluster.local:5000",
  "model_loaded": true
}
```

---

## 💻 Python Client Example

```python
import requests
import time

# Configuration
API_BASE = "http://localhost:8000"

# Training script
training_script = """
import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Sample data
data = pd.DataFrame({
    'feature1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    'feature2': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    'target': [0, 0, 1, 1, 0, 1, 1, 0, 1, 1]
})

X = data[['feature1', 'feature2']]
y = data['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train with MLflow
with mlflow.start_run():
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X_train, y_train)

    # IMPORTANT: Use mlflow.sklearn.log_model
    mlflow.sklearn.log_model(model, "model")

    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)

    print(f"Model trained with accuracy: {accuracy}")
"""

# Deploy model (single API call)
print("🚀 Deploying model...")
print("⏳ This will take 3-5 minutes (training, building, pushing, deploying)...\n")

start_time = time.time()

response = requests.post(
    f"{API_BASE}/mlops/deploy",
    json={
        "script_name": "train_model.py",
        "script_content": training_script,
        "experiment_name": "production_experiment",
        "model_name": "my_production_model",
        "requirements": ["scikit-learn==1.3.2", "pandas==2.1.3"],
        "replicas": 2,
        "namespace": "asgard"
    },
    timeout=600  # 10 minutes timeout
)

deployment_time = time.time() - start_time

# Check response
if response.status_code == 200:
    result = response.json()

    print(f"🎉 Deployment successful in {deployment_time:.1f}s!")
    print(f"\n📊 Deployment Details:")
    print(f"   Model: {result['model_name']} v{result['model_version']}")
    print(f"   Status: {result['status']}")
    print(f"   Inference URL: {result['inference_url']}")
    print(f"   External IP: {result['external_ip']}")
    print(f"   ECR Image: {result['ecr_image']}")
    print(f"   MLflow Run: {result['run_id']}")

    # Save inference URL
    inference_url = result['inference_url']

    print(f"\n🧪 Testing deployed model...")

    # Test health
    health = requests.get(f"{inference_url}/health").json()
    print(f"   Health: {health['status']}")

    # Make prediction
    pred_response = requests.post(
        f"{inference_url}/predict",
        json={
            "inputs": {
                "feature1": [1, 5, 10],
                "feature2": [2, 10, 20]
            }
        }
    )

    if pred_response.status_code == 200:
        predictions = pred_response.json()
        print(f"   Predictions: {predictions['predictions']}")
        print(f"\n✅ Model is ready for production!")
        print(f"   Use: {inference_url}/predict")
    else:
        print(f"   ⚠️ Prediction test failed: {pred_response.text}")

else:
    print(f"❌ Deployment failed: {response.status_code}")
    print(response.text)
```

---

## ⚡ Key Differences from Before

### Old Approach (Async)

```python
# 1. Deploy (returns immediately)
response = requests.post("/mlops/deploy", json={...})
job_id = response.json()["job_id"]

# 2. Poll for status (manual polling required)
while True:
    status = requests.get(f"/mlops/deployments/{job_id}").json()
    if status["status"] == "deployed":
        inference_url = status["deployment_url"]
        break
    time.sleep(30)

# 3. Use model
requests.post(f"{inference_url}/predict", ...)
```

### New Approach (Sync) ✨

```python
# 1. Deploy (waits for completion, returns URL directly)
response = requests.post("/mlops/deploy", json={...}, timeout=600)
inference_url = response.json()["inference_url"]

# 2. Use model immediately!
requests.post(f"{inference_url}/predict", ...)
```

---

## 🔧 Configuration

### Required Environment Variables

```bash
# MLflow
MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000

# AWS ECR
ECR_REGISTRY=637423187518.dkr.ecr.eu-north-1.amazonaws.com
ECR_REPO=asgard-model
AWS_DEFAULT_REGION=eu-north-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

### Request Parameters

| Parameter          | Type    | Required | Default  | Description                          |
| ------------------ | ------- | -------- | -------- | ------------------------------------ |
| `script_name`      | string  | ✅       | -        | Training script name                 |
| `script_content`   | string  | ✅       | -        | Python script (plain text or base64) |
| `experiment_name`  | string  | ✅       | -        | MLflow experiment                    |
| `model_name`       | string  | ✅       | -        | Model name for registry & deployment |
| `requirements`     | array   | ❌       | []       | Pip packages                         |
| `environment_vars` | object  | ❌       | {}       | Environment variables                |
| `timeout`          | integer | ❌       | 300      | Training timeout (60-3600s)          |
| `tags`             | object  | ❌       | {}       | MLflow run tags                      |
| `replicas`         | integer | ❌       | 2        | K8s replicas (1-10)                  |
| `namespace`        | string  | ❌       | "asgard" | K8s namespace                        |

---

## 📊 Response Fields

| Field                     | Type   | Description               |
| ------------------------- | ------ | ------------------------- |
| `model_name`              | string | Deployed model name       |
| `experiment_name`         | string | MLflow experiment         |
| `status`                  | string | "deployed" or "failed"    |
| `inference_url`           | string | **Main inference URL** ⭐ |
| `external_ip`             | string | LoadBalancer IP           |
| `model_version`           | string | Model version in registry |
| `run_id`                  | string | MLflow run ID             |
| `ecr_image`               | string | Full ECR image URI        |
| `endpoints`               | object | All available endpoints   |
| `deployment_time_seconds` | float  | Total deployment time     |
| `message`                 | string | Success/error message     |

---

## ⚠️ Important Notes

### Client-Side Configuration

**Set appropriate timeout:**

```python
# Deployment takes 3-5 minutes on average
requests.post(url, json=data, timeout=600)  # 10 minutes
```

**Handle errors:**

```python
try:
    response = requests.post(url, json=data, timeout=600)
    response.raise_for_status()
    result = response.json()

    if result["status"] == "deployed":
        print(f"Success! URL: {result['inference_url']}")
    else:
        print(f"Failed: {result.get('message', 'Unknown error')}")

except requests.Timeout:
    print("Deployment timeout - may still be processing")
except requests.RequestException as e:
    print(f"Request failed: {e}")
```

### Training Script Requirements

**Must include:**

```python
import mlflow

with mlflow.start_run():
    # Train your model
    model = YourModel()
    model.fit(X, y)

    # CRITICAL: Log model with mlflow
    mlflow.sklearn.log_model(model, "model")
    # or mlflow.xgboost.log_model()
    # or mlflow.tensorflow.log_model()

    # Optional: Log metrics
    mlflow.log_metric("accuracy", accuracy)
```

---

## 🎯 Use Cases

### 1. Production Deployment

```bash
# Deploy to production in one call
curl -X POST /mlops/deploy -d '{
  "model_name": "production_model",
  "replicas": 5,
  ...
}'

# Get URL, update config
```

### 2. A/B Testing

```bash
# Deploy version A
RESPONSE_A=$(curl -X POST /mlops/deploy -d '{"model_name": "model_v1", ...}')
URL_A=$(echo $RESPONSE_A | jq -r '.inference_url')

# Deploy version B
RESPONSE_B=$(curl -X POST /mlops/deploy -d '{"model_name": "model_v2", ...}')
URL_B=$(echo $RESPONSE_B | jq -r '.inference_url')

# Split traffic between URL_A and URL_B
```

### 3. Quick Experimentation

```python
# Quickly test different models
for model_type in ["random_forest", "gradient_boosting", "neural_net"]:
    script = generate_training_script(model_type)

    result = deploy_model(
        model_name=f"experiment_{model_type}",
        script_content=script
    )

    # Test immediately
    test_model(result["inference_url"])
```

---

## 🔍 Troubleshooting

### Deployment Takes Too Long

- **Typical time**: 3-5 minutes
- **Check**: ECR push (slowest step)
- **Action**: Ensure good network connectivity

### Timeout Error

```python
# Increase timeout
requests.post(url, json=data, timeout=900)  # 15 minutes
```

### Training Fails

- **Check**: Script has `mlflow.sklearn.log_model()`
- **Check**: All required packages in `requirements`
- **Check**: Script syntax is correct

### External IP Not Assigned

- **Wait**: LoadBalancer may take 2-3 minutes
- **Check**: Cloud provider LoadBalancer quota
- **Verify**: `kubectl get svc -n asgard`

---

## 📚 Related Documentation

- **docs/MLOPS_API_CLEANUP.md** - API reorganization details
- **docs/MLOPS_QUICK_REFERENCE.md** - Quick reference
- **ONE_CLICK_DEPLOYMENT.md** - Original deployment guide

---

## ✅ Summary

**Before**: Deploy → Poll → Get URL → Use  
**Now**: Deploy → Get URL → Use ✨

**One API call. One response. Ready to use.**

Your model is deployed and the inference URL is in the response. Start making predictions immediately! 🚀
