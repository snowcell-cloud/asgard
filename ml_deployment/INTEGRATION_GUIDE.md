# Automated ML Model Deployment - Integration Guide

## 🎯 Overview

This integrated solution automatically deploys ML models to OVH EKS after training completes:

```
Training Script → MLOps API → MLflow → Docker Build → ECR Push → EKS Deploy → Inference Endpoint
```

## 🔄 Complete Workflow

### 1. Upload Training Script via API

```bash
python3 ml_deployment/upload_and_deploy.py
```

This script:

- ✅ Uploads `train_with_feast.py` to `/mlops/training/upload`
- ✅ Monitors training progress
- ✅ Shows deployment status
- ✅ Provides inference endpoint details

### 2. What Happens Automatically

Once you upload the training script:

**Step 1: Training (MLOps API)**

- Script executes with MLflow tracking
- Fetches features from Feast (gold layer) or uses synthetic data
- Trains RandomForest classifier
- Logs metrics and parameters to MLflow
- Registers model to MLflow Model Registry

**Step 2: Containerization (Automated)**

- Builds Docker image with trained model
- Includes FastAPI inference service
- Tags image: `<model_name>-v<version>`

**Step 3: ECR Push (Automated)**

- Authenticates with AWS ECR
- Pushes to: `637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model`

**Step 4: EKS Deployment (Automated)**

- Deploys to OVH EKS cluster
- Namespace: `asgard`
- Creates:
  - Deployment (2 replicas)
  - Service (ClusterIP)
  - Health checks
  - Resource limits

**Step 5: Inference Ready**

- REST API available at: `http://<model_name>-inference.asgard.svc.cluster.local`
- Endpoints:
  - `GET /health`
  - `GET /metadata`
  - `POST /predict`

## 📋 Quick Start

### Prerequisites

```bash
# 1. Port-forward MLOps API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# 2. Verify connectivity
curl http://localhost:8000/mlops/status

# 3. Ensure AWS credentials are configured
aws sts get-caller-identity
```

### Option A: Automated Workflow (Recommended)

```bash
# Run the complete workflow
cd /home/hac/downloads/code/asgard-dev
python3 ml_deployment/upload_and_deploy.py
```

### Option B: Manual Upload

```bash
# Encode training script
SCRIPT_B64=$(base64 -w 0 ml_deployment/train_with_feast.py)

# Upload to API
curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d "{
    \"script_name\": \"train_with_feast.py\",
    \"script_content\": \"$SCRIPT_B64\",
    \"experiment_name\": \"feast_deployment_demo\",
    \"model_name\": \"churn_predictor_feast\",
    \"requirements\": [\"feast\", \"scikit-learn\", \"pandas\", \"numpy\"],
    \"environment_vars\": {
      \"USE_FEAST\": \"false\",
      \"MODEL_NAME\": \"churn_predictor_feast\"
    },
    \"timeout\": 600,
    \"tags\": {
      \"version\": \"1.0\",
      \"deployment\": \"automated\"
    }
  }"

# Get job ID from response, then monitor:
JOB_ID="<job-id-from-response>"
curl http://localhost:8000/mlops/training/jobs/$JOB_ID | jq
```

## 🔍 Monitor Deployment

### Check Training Status

```bash
# Via API
curl http://localhost:8000/mlops/training/jobs/<JOB_ID> | jq

# Watch logs
watch -n 2 'curl -s http://localhost:8000/mlops/training/jobs/<JOB_ID> | jq .logs'
```

### Check EKS Deployment

```bash
# List all resources
kubectl get all -n asgard -l app=churn_predictor_feast-inference

# Check pods
kubectl get pods -n asgard -l app=churn_predictor_feast-inference

# View logs
kubectl logs -n asgard -l app=churn_predictor_feast-inference -f

# Check service
kubectl get svc -n asgard -l app=churn_predictor_feast-inference
```

### Check ECR Image

```bash
# List images in ECR
aws ecr list-images \
  --repository-name asgard-model \
  --registry-id 637423187518 \
  --region eu-north-1

# Get image details
aws ecr describe-images \
  --repository-name asgard-model \
  --registry-id 637423187518 \
  --region eu-north-1 \
  --image-ids imageTag=churn_predictor_feast-v1
```

## 🧪 Test Inference Endpoint

### Option A: Port-Forward (Development)

```bash
# Forward service to localhost
kubectl port-forward -n asgard svc/churn_predictor_feast-inference 8080:80 &

# Test health
curl http://localhost:8080/health

# Test metadata
curl http://localhost:8080/metadata

# Test prediction
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "total_purchases": [10, 25, 5],
      "avg_purchase_value": [50.0, 120.5, 30.0],
      "days_since_last_purchase": [5, 15, 200],
      "customer_lifetime_value": [500.0, 3000.0, 150.0],
      "account_age_days": [365, 730, 180],
      "support_tickets_count": [2, 1, 8]
    },
    "return_probabilities": true
  }'
```

### Option B: Inside Cluster

```bash
# From another pod in the cluster
curl http://churn_predictor_feast-inference.asgard.svc.cluster.local/health
```

## ⚙️ Configuration

### Environment Variables (Training Script)

These are automatically injected by the MLOps API:

| Variable              | Description         | Default                   |
| --------------------- | ------------------- | ------------------------- |
| `MLFLOW_TRACKING_URI` | MLflow server URL   | Auto-configured           |
| `EXPERIMENT_NAME`     | MLflow experiment   | From API request          |
| `MODEL_NAME`          | Model registry name | From API request          |
| `FEAST_REPO_PATH`     | Feast repository    | `/tmp/feast_repo`         |
| `USE_FEAST`           | Use Feast features  | `false`                   |
| `FEATURE_VIEW_NAME`   | Feast feature view  | `customer_churn_features` |

### Deployment Configuration

Edit `app/mlops/deployment_service.py` to change:

- **ECR Registry**: `self.ecr_registry = "637423187518.dkr.ecr.eu-north-1.amazonaws.com"`
- **ECR Repository**: `self.ecr_repository = "asgard-model"`
- **AWS Region**: `self.aws_region = "eu-north-1"`
- **K8s Namespace**: `self.k8s_namespace = "asgard"`
- **Replicas**: Default 2, edit in `_deploy_to_eks()` method

## 🎛️ Advanced Usage

### Custom Training Script

Your training script must:

1. Use `mlflow.start_run()` for tracking
2. Call `mlflow.log_model()` or `mlflow.sklearn.log_model()`
3. Handle environment variables injected by API

Example minimal script:

```python
import os
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier

# MLflow is auto-configured by API
with mlflow.start_run() as run:
    # Your training code
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    # Log model (required for auto-deployment)
    mlflow.sklearn.log_model(model, "model")

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)

    print(f"Run ID: {run.info.run_id}")
```

### Using Feast Features

Set `USE_FEAST=true` in environment variables:

```json
{
  "environment_vars": {
    "USE_FEAST": "true",
    "FEATURE_VIEW_NAME": "your_feature_view"
  }
}
```

Your training script will then fetch features from the Feast gold layer.

### Multiple Models

Deploy multiple models to the same namespace:

```bash
# Model 1: Churn prediction
python3 upload_and_deploy.py  # model_name="churn_predictor_feast"

# Model 2: Fraud detection
python3 upload_and_deploy.py  # model_name="fraud_detector_feast"

# Both will be deployed to asgard namespace
kubectl get svc -n asgard
# churn_predictor_feast-inference
# fraud_detector_feast-inference
```

## 🔧 Troubleshooting

### Issue: Training Fails

```bash
# Check job logs
curl http://localhost:8000/mlops/training/jobs/<JOB_ID> | jq .logs

# Common fixes:
# - Ensure requirements are installable
# - Check MLflow connectivity
# - Verify Feast feature view exists (if USE_FEAST=true)
```

### Issue: Docker Build Fails

```bash
# Check deployment service logs
kubectl logs -n asgard -l app=asgard-app --tail=200 | grep -A 20 "Docker build"

# Common fixes:
# - Verify inference_service.py exists
# - Check Dockerfile syntax
# - Ensure Docker daemon is accessible
```

### Issue: ECR Push Fails

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check ECR permissions
aws ecr describe-repositories --region eu-north-1

# Common fixes:
# - Update AWS credentials
# - Verify ECR repository exists
# - Check IAM permissions for ECR push
```

### Issue: EKS Deployment Fails

```bash
# Check deployment events
kubectl describe deployment -n asgard <model_name>-inference

# Check pod events
kubectl describe pod -n asgard -l app=<model_name>-inference

# Common fixes:
# - Verify image pull secrets
# - Check resource quotas
# - Ensure namespace exists
# - Verify MLflow service accessibility
```

### Issue: Inference Returns Errors

```bash
# Check pod logs
kubectl logs -n asgard -l app=<model_name>-inference

# Test model loading
kubectl exec -n asgard <pod-name> -- python -c "
import mlflow
mlflow.set_tracking_uri('http://mlflow-service.asgard.svc.cluster.local:5000')
model = mlflow.sklearn.load_model('models:/<model_name>/latest')
print('Model loaded successfully')
"

# Common fixes:
# - Verify model exists in MLflow
# - Check feature names match training data
# - Ensure input format is correct
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Training Phase                             │
│                                                                 │
│  User → upload_and_deploy.py → /mlops/training/upload          │
│                                         ↓                       │
│                              MLOps Service (pod)                │
│                                         ↓                       │
│                         Execute train_with_feast.py             │
│                                         ↓                       │
│                   Feast (gold layer) ← → MLflow                │
│                                         ↓                       │
│                          Register Model                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Automated Deployment                          │
│                                                                 │
│  ModelDeploymentService (auto-triggered)                        │
│                    ↓                                            │
│         Build Docker Image (Dockerfile + inference_service.py)  │
│                    ↓                                            │
│         Push to ECR (637423187518.../asgard-model)             │
│                    ↓                                            │
│         Deploy to EKS (asgard namespace)                        │
│                    ↓                                            │
│         Create Deployment + Service                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Inference Phase                               │
│                                                                 │
│  Client → Port-Forward or Ingress                              │
│                    ↓                                            │
│         Inference Service (FastAPI)                             │
│                    ↓                                            │
│         Load Model from MLflow                                  │
│                    ↓                                            │
│         Return Predictions                                      │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Summary

**What You Built:**

- ✅ Integrated training → deployment pipeline
- ✅ Automatic Docker image creation
- ✅ ECR push to: `637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model`
- ✅ EKS deployment to `asgard` namespace
- ✅ Inference endpoints automatically created

**One Command:**

```bash
python3 ml_deployment/upload_and_deploy.py
```

**Result:**

- Trained model in MLflow ✅
- Docker image in ECR ✅
- Running deployment in EKS ✅
- Inference API ready ✅

---

**Last Updated:** November 7, 2025  
**Target Cluster:** OVH EKS  
**Target Namespace:** asgard  
**ECR Repository:** 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model
