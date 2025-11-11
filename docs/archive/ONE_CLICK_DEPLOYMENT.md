# 🚀 ONE-CLICK MODEL DEPLOYMENT API

## Overview

**NEW ENDPOINT**: `/mlops/deploy` - Complete ML deployment pipeline in a single API call!

This endpoint streamlines the entire ML deployment workflow:

1. ✅ **Train** - Execute training script with MLflow tracking
2. ✅ **Build** - Create optimized Docker image (multi-stage)
3. ✅ **Push** - Upload image to AWS ECR
4. ✅ **Deploy** - Deploy to Kubernetes with LoadBalancer
5. ✅ **Return URL** - Get public inference endpoint

---

## API Endpoint

### `POST /mlops/deploy`

**Base URL**: `http://localhost:8000`

**Full Endpoint**: `http://localhost:8000/mlops/deploy`

---

## Request Schema

```json
{
  "script_name": "train_model.py",
  "script_content": "<base64-encoded-script-or-plain-text>",
  "experiment_name": "production_experiment",
  "model_name": "customer_churn_model",
  "requirements": ["scikit-learn", "pandas", "numpy"],
  "environment_vars": {},
  "timeout": 300,
  "tags": { "version": "1.0", "team": "ml-team" },
  "replicas": 2,
  "namespace": "asgard"
}
```

### Parameters

| Parameter          | Type    | Required | Default  | Description                          |
| ------------------ | ------- | -------- | -------- | ------------------------------------ |
| `script_name`      | string  | ✅       | -        | Name for the training script         |
| `script_content`   | string  | ✅       | -        | Python script (base64 or plain text) |
| `experiment_name`  | string  | ✅       | -        | MLflow experiment name               |
| `model_name`       | string  | ✅       | -        | Model name for registry & deployment |
| `requirements`     | array   | ❌       | []       | Additional pip packages              |
| `environment_vars` | object  | ❌       | {}       | Environment variables for training   |
| `timeout`          | integer | ❌       | 300      | Training timeout (60-3600 seconds)   |
| `tags`             | object  | ❌       | {}       | MLflow run tags                      |
| `replicas`         | integer | ❌       | 2        | Kubernetes replicas (1-10)           |
| `namespace`        | string  | ❌       | "asgard" | Kubernetes namespace                 |

---

## Response

### Immediate Response (202 Accepted)

```json
{
  "job_id": "a3b4c5d6",
  "model_name": "customer_churn_model",
  "experiment_name": "production_experiment",
  "status": "training",
  "message": "Deployment started. Use /mlops/deployments/a3b4c5d6 to check status"
}
```

---

## Check Deployment Status

### `GET /mlops/deployments/{job_id}`

**Example**: `GET http://localhost:8000/mlops/deployments/a3b4c5d6`

### Status Response

```json
{
  "job_id": "a3b4c5d6",
  "model_name": "customer_churn_model",
  "experiment_name": "production_experiment",
  "status": "deployed",
  "deployment_url": "http://51.89.136.142",
  "external_ip": "51.89.136.142",
  "model_version": "1",
  "run_id": "7da8457f3fa04a6189fb3fce7ebb0259",
  "ecr_image": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model:customer-churn-model-v1",
  "error": null,
  "created_at": "2025-11-11T10:30:00Z",
  "completed_at": "2025-11-11T10:35:00Z",
  "duration_seconds": 300
}
```

### Status Values

| Status      | Description                              |
| ----------- | ---------------------------------------- |
| `training`  | Training model with MLflow               |
| `building`  | Building Docker image                    |
| `pushing`   | Pushing image to ECR                     |
| `deploying` | Deploying to Kubernetes                  |
| `deployed`  | ✅ Successfully deployed                 |
| `failed`    | ❌ Deployment failed (check error field) |

---

## Complete Example

### 1. Prepare Training Script

```python
# train_model.py
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
with mlflow.start_run() as run:
    model = RandomForestClassifier(n_estimators=10)
    model.fit(X_train, y_train)

    # Log model
    mlflow.sklearn.log_model(model, "model")

    # Log metrics
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)

    print(f"Model trained with accuracy: {accuracy}")
```

### 2. Encode Script (Optional)

```bash
# Base64 encode the script
cat train_model.py | base64 -w 0 > encoded_script.txt
```

Or use plain text directly in the API request.

### 3. Send Deployment Request

```bash
curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train_model.py",
    "script_content": "'"$(cat train_model.py)"'",
    "experiment_name": "production_experiment",
    "model_name": "my_model",
    "requirements": ["scikit-learn==1.3.2", "pandas==2.1.3"],
    "replicas": 2,
    "namespace": "asgard"
  }'
```

**Response**:

```json
{
  "job_id": "7f3e9a2b",
  "model_name": "my_model",
  "experiment_name": "production_experiment",
  "status": "training",
  "message": "Deployment started. Use /mlops/deployments/7f3e9a2b to check status"
}
```

### 4. Check Deployment Status

```bash
# Poll every 30 seconds
watch -n 30 'curl -s http://localhost:8000/mlops/deployments/7f3e9a2b | jq .'
```

### 5. Once Deployed, Test the Model

```bash
# Health check
curl http://51.89.136.142/health

# Get metadata
curl http://51.89.136.142/metadata

# Make predictions
curl -X POST http://51.89.136.142/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "feature1": [1, 2, 3],
      "feature2": [2, 4, 6]
    }
  }'
```

**Response**:

```json
{
  "predictions": [0, 0, 1]
}
```

---

## Deployed Service Endpoints

Once deployment is complete, your model is accessible at the `deployment_url`:

### `GET /health`

Health check endpoint

```json
{
  "status": "healthy",
  "model": {
    "name": "my_model",
    "version": "1",
    "run_id": "7da8457f3fa04a6189fb3fce7ebb0259"
  }
}
```

### `GET /metadata`

Model metadata

```json
{
  "model_name": "my_model",
  "model_version": "1",
  "run_id": "7da8457f3fa04a6189fb3fce7ebb0259",
  "mlflow_uri": "http://mlflow-service.asgard.svc.cluster.local:5000",
  "model_loaded": true
}
```

### `POST /predict`

Make predictions

**Request**:

```json
{
  "inputs": {
    "feature1": [1, 2, 3],
    "feature2": [2, 4, 6]
  }
}
```

**Response**:

```json
{
  "predictions": [0, 0, 1]
}
```

### `GET /`

API information

```json
{
  "service": "Model Inference API",
  "model": "my_model",
  "version": "1"
}
```

---

## Python Client Example

```python
import requests
import json
import time
import base64

# Configuration
API_BASE = "http://localhost:8000"

# Read and prepare training script
with open("train_model.py", "r") as f:
    script_content = f.read()

# Create deployment request
deployment_request = {
    "script_name": "train_model.py",
    "script_content": script_content,
    "experiment_name": "production_experiment",
    "model_name": "my_production_model",
    "requirements": ["scikit-learn==1.3.2", "pandas==2.1.3"],
    "timeout": 300,
    "tags": {"version": "1.0", "env": "production"},
    "replicas": 2,
    "namespace": "asgard"
}

# Submit deployment
print("🚀 Submitting deployment...")
response = requests.post(
    f"{API_BASE}/mlops/deploy",
    json=deployment_request
)
response.raise_for_status()

result = response.json()
job_id = result["job_id"]
print(f"✅ Deployment started: {job_id}")

# Poll for completion
print("\n⏳ Waiting for deployment...")
while True:
    status_response = requests.get(f"{API_BASE}/mlops/deployments/{job_id}")
    status = status_response.json()

    current_status = status["status"]
    print(f"   Status: {current_status}")

    if current_status == "deployed":
        print(f"\n🎉 Deployment successful!")
        print(f"   URL: {status['deployment_url']}")
        print(f"   External IP: {status['external_ip']}")
        print(f"   Model Version: {status['model_version']}")
        print(f"   ECR Image: {status['ecr_image']}")

        # Test the deployed model
        deployment_url = status['deployment_url']

        print(f"\n🧪 Testing deployed model...")

        # Health check
        health = requests.get(f"{deployment_url}/health").json()
        print(f"   Health: {health['status']}")

        # Make prediction
        pred_response = requests.post(
            f"{deployment_url}/predict",
            json={
                "inputs": {
                    "feature1": [1, 2, 3],
                    "feature2": [2, 4, 6]
                }
            }
        )
        predictions = pred_response.json()
        print(f"   Predictions: {predictions['predictions']}")

        break

    elif current_status == "failed":
        print(f"\n❌ Deployment failed: {status['error']}")
        break

    time.sleep(30)  # Check every 30 seconds
```

---

## Architecture

### Deployment Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    POST /mlops/deploy                       │
│                    (Single API Call)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   1. TRAIN MODEL       │
        │   - Execute script     │
        │   - MLflow tracking    │
        │   - Register model     │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   2. BUILD IMAGE       │
        │   - Multi-stage build  │
        │   - Optimize layers    │
        │   - Include inference  │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   3. PUSH TO ECR       │
        │   - ECR authentication │
        │   - Upload layers      │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   4. DEPLOY TO K8S     │
        │   - Create deployment  │
        │   - LoadBalancer SVC   │
        │   - Wait for IP        │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   5. RETURN URL        │
        │   http://EXTERNAL-IP   │
        └────────────────────────┘
```

### Infrastructure Components

- **MLflow**: Model registry and tracking
- **AWS ECR**: Container registry
- **Kubernetes**: Container orchestration
- **LoadBalancer**: External access

---

## Environment Variables

Required environment variables on the MLOps service:

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

---

## Features

### ✅ Implemented

1. **Asynchronous Deployment** - Returns immediately, runs in background
2. **Status Tracking** - Poll deployment progress
3. **Multi-stage Docker Build** - Optimized image size
4. **ECR Integration** - Automatic push to container registry
5. **LoadBalancer Service** - Public IP assignment
6. **Health Endpoints** - Built-in health checks
7. **MLflow Integration** - Full model tracking
8. **Error Handling** - Detailed error messages
9. **Resource Limits** - CPU/Memory constraints
10. **Image Pull Secrets** - ECR authentication for K8s

### 🎯 Best Practices

- **Timeouts**: Training timeout configurable (60-3600s)
- **Replicas**: 1-10 pods for high availability
- **Probes**: Liveness and readiness checks
- **Secrets**: AWS credentials injected securely
- **Logging**: Comprehensive logging throughout pipeline
- **Thread Safety**: Thread-safe job storage

---

## Troubleshooting

### Deployment Stuck in "training"

- Check training logs via `/mlops/deployments/{job_id}`
- Verify script has `mlflow.sklearn.log_model()` call
- Ensure timeout is sufficient for your model

### Deployment Stuck in "pushing"

- Verify AWS credentials are configured
- Check ECR repository exists
- Ensure network connectivity to ECR

### Deployment Stuck in "deploying"

- Verify Kubernetes cluster is accessible
- Check ECR credentials secret exists: `kubectl get secret ecr-credentials -n asgard`
- Verify namespace exists: `kubectl get ns asgard`

### External IP not assigned

- LoadBalancer may take 2-3 minutes to provision
- Check cloud provider LoadBalancer quota
- Verify service: `kubectl get svc -n asgard`

### Model not loading in pods

- Check training script uses `mlflow.sklearn.log_model()` properly
- Verify MLflow run has model artifact
- Check pod logs: `kubectl logs -n asgard -l app=<deployment-name>`

---

## Comparison: Old vs New Workflow

### Old Workflow (4 steps)

```bash
# 1. Upload and train
curl -X POST /mlops/training/upload -d '{...}'
# Get job_id, wait...

# 2. Build Docker image
docker build -t myimage .
docker tag myimage ECR_URI

# 3. Push to ECR
aws ecr get-login-password | docker login...
docker push ECR_URI

# 4. Deploy to K8s
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
# Wait for IP...
```

### New Workflow (1 step)

```bash
# ONE API CALL - Everything automated!
curl -X POST /mlops/deploy -d '{
  "script_content": "...",
  "model_name": "my_model",
  ...
}'

# Poll status
curl /mlops/deployments/{job_id}

# Done! Get deployment_url
```

---

## Benefits

1. **🚀 Faster Deployment** - Single API call vs multiple manual steps
2. **🔄 Reproducible** - Consistent deployment process
3. **📊 Trackable** - Full visibility into deployment status
4. **🔒 Secure** - Automated credential management
5. **⚡ Efficient** - Optimized Docker builds
6. **🌐 Production-Ready** - LoadBalancer with external IP
7. **🛡️ Resilient** - Health checks and multiple replicas
8. **📝 Auditable** - Complete deployment history

---

## Next Steps

1. **Database Storage** - Persist deployment jobs (currently in-memory)
2. **Webhooks** - Notify on deployment completion
3. **Auto-scaling** - HPA for deployed models
4. **Monitoring** - Prometheus metrics
5. **A/B Testing** - Traffic splitting between versions
6. **Rollback** - One-click rollback to previous version

---

**Ready to deploy?** Use the `/mlops/deploy` endpoint and get your model in production with a single API call! 🚀
