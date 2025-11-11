# ML Model Deployment Pipeline

Complete end-to-end ML model deployment solution with **Feast feature store**, **MLflow**, and **EKS**.

## 📋 Overview

This deployment pipeline enables you to:

1. ✅ Train ML models using features from Feast feature store
2. ✅ Track experiments and models with MLflow
3. ✅ Build production-ready Docker images
4. ✅ Deploy to AWS EKS with auto-scaling
5. ✅ Expose inference endpoints (REST API)

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Feast     │─────▶│   Training  │─────▶│   MLflow    │
│ Feature     │      │   Script    │      │  Registry   │
│   Store     │      └─────────────┘      └─────────────┘
└─────────────┘              │                     │
                             │                     │
                             ▼                     ▼
                      ┌─────────────┐      ┌─────────────┐
                      │   Docker    │      │   Model     │
                      │   Image     │◀─────│  Artifacts  │
                      └─────────────┘      └─────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │     EKS     │
                      │  Deployment │
                      └─────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │  Inference  │
                      │     API     │
                      └─────────────┘
```

## 📁 Project Structure

```
ml_deployment/
├── train_with_feast.py          # Training script with Feast integration
├── inference_service.py          # FastAPI inference service
├── requirements.txt              # Python dependencies
├── Dockerfile.inference          # Multi-stage production Dockerfile
├── deploy.sh                     # End-to-end deployment automation
├── k8s/
│   └── deployment.yaml           # Kubernetes manifests (all resources)
└── README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

```bash
# Required tools
- Docker
- kubectl
- AWS CLI
- Python 3.11+

# Required environment variables
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="eu-north-1"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

### One-Command Deployment

```bash
# Complete end-to-end deployment
./ml_deployment/deploy.sh
```

This will:

1. Train the model
2. Build Docker image
3. Push to ECR
4. Deploy to EKS
5. Test inference endpoints

### Partial Deployment

```bash
# Skip training (use existing model)
./ml_deployment/deploy.sh --skip-train

# Skip Docker build (use existing image)
./ml_deployment/deploy.sh --skip-build

# Only build and push (no deploy)
./ml_deployment/deploy.sh --skip-deploy --skip-test
```

## 📚 Detailed Steps

### Step 1: Train Model with Feast Features

```bash
# Set environment variables
export MLFLOW_TRACKING_URI="http://localhost:5000"
export MODEL_NAME="churn_predictor_feast"
export EXPERIMENT_NAME="feast_ml_deployment"
export FEAST_REPO_PATH="/tmp/feast_repo"

# Port-forward to MLflow
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# Run training
python3 ml_deployment/train_with_feast.py
```

**Training Script Features:**

- ✅ Fetches features from Feast feature store
- ✅ Trains RandomForest classifier
- ✅ Logs all metrics to MLflow
- ✅ Registers model to MLflow Model Registry
- ✅ Saves artifacts for deployment

### Step 2: Build Docker Image

```bash
# Set variables
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="eu-north-1"
export ECR_REPOSITORY="ml-inference"
export IMAGE_TAG="latest"

# Build image
docker build \
  -f ml_deployment/Dockerfile.inference \
  -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG} \
  .

# Test locally
docker run -p 8080:8080 \
  -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" \
  -e MODEL_NAME="churn_predictor_feast" \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}
```

### Step 3: Push to AWS ECR

```bash
# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Create repository (if not exists)
aws ecr create-repository \
  --repository-name ${ECR_REPOSITORY} \
  --region ${AWS_REGION} \
  --image-scanning-configuration scanOnPush=true

# Push image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}
```

### Step 4: Deploy to EKS

```bash
# Update kubeconfig
aws eks update-kubeconfig --name asgard-cluster --region ${AWS_REGION}

# Create namespace
kubectl create namespace ml-inference

# Create AWS credentials secret
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -n ml-inference

# Update deployment.yaml with your image URI
sed -i "s|<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/ml-inference:latest|${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}|g" \
  ml_deployment/k8s/deployment.yaml

# Deploy
kubectl apply -f ml_deployment/k8s/deployment.yaml

# Check deployment status
kubectl rollout status deployment/ml-inference -n ml-inference

# View pods
kubectl get pods -n ml-inference
```

### Step 5: Access Inference API

#### Option A: Port-Forward (Development)

```bash
# Forward service to localhost
kubectl port-forward -n ml-inference svc/ml-inference-service 8080:80

# Access API
curl http://localhost:8080/health
```

#### Option B: Ingress (Production)

1. Update `ml_deployment/k8s/deployment.yaml`:

   ```yaml
   spec:
     tls:
       - hosts:
           - ml-inference.yourdomain.com # Your domain
   ```

2. Update DNS:

   ```bash
   # Get ingress IP
   kubectl get ingress ml-inference-ingress -n ml-inference

   # Add A record: ml-inference.yourdomain.com → <INGRESS_IP>
   ```

3. Access API:
   ```bash
   curl https://ml-inference.yourdomain.com/health
   ```

## 🔧 API Usage

### Health Check

```bash
curl http://localhost:8080/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T10:00:00",
  "model_loaded": true,
  "model_name": "churn_predictor_feast",
  "model_version": "1"
}
```

### Model Metadata

```bash
curl http://localhost:8080/metadata
```

**Response:**

```json
{
  "model_name": "churn_predictor_feast",
  "model_version": "1",
  "mlflow_run_id": "abc123def456",
  "loaded_at": "2025-11-06T10:00:00",
  "feature_names": ["total_purchases", "avg_purchase_value", ...],
  "model_type": "RandomForestClassifier"
}
```

### Single Prediction

```bash
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

**Response:**

```json
{
  "predictions": [0, 0, 1],
  "probabilities": [
    [0.92, 0.08],
    [0.88, 0.12],
    [0.15, 0.85]
  ],
  "inference_time_ms": 8.5,
  "timestamp": "2025-11-06T10:00:00",
  "model_name": "churn_predictor_feast",
  "model_version": "1"
}
```

### Batch Prediction

```bash
curl -X POST http://localhost:8080/batch_predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [
      {
        "total_purchases": 10,
        "avg_purchase_value": 50.0,
        "days_since_last_purchase": 5,
        "customer_lifetime_value": 500.0,
        "account_age_days": 365,
        "support_tickets_count": 2
      },
      {
        "total_purchases": 25,
        "avg_purchase_value": 120.5,
        "days_since_last_purchase": 15,
        "customer_lifetime_value": 3000.0,
        "account_age_days": 730,
        "support_tickets_count": 1
      }
    ],
    "return_probabilities": true
  }'
```

## 🐍 Python Client

```python
import requests

class MLInferenceClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url

    def predict(self, inputs, return_probabilities=False):
        response = requests.post(
            f"{self.base_url}/predict",
            json={
                "inputs": inputs,
                "return_probabilities": return_probabilities
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = MLInferenceClient()

result = client.predict(
    inputs={
        "total_purchases": [10, 25],
        "avg_purchase_value": [50.0, 120.5],
        "days_since_last_purchase": [5, 15],
        "customer_lifetime_value": [500.0, 3000.0],
        "account_age_days": [365, 730],
        "support_tickets_count": [2, 1]
    },
    return_probabilities=True
)

print(f"Predictions: {result['predictions']}")
print(f"Probabilities: {result['probabilities']}")
```

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
kubectl logs -n ml-inference -l app=ml-inference -f

# Logs from specific pod
kubectl logs -n ml-inference <pod-name> -f
```

### Check Metrics

```bash
# Pod metrics
kubectl top pods -n ml-inference

# HPA status
kubectl get hpa -n ml-inference

# Deployment status
kubectl get deployment ml-inference -n ml-inference -o wide
```

### MLflow UI

```bash
# Port-forward MLflow
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# Open browser
open http://localhost:5000
```

## 🔄 Update Deployment

### Deploy New Model Version

```bash
# Train new model version
export MODEL_NAME="churn_predictor_feast_v2"
python3 ml_deployment/train_with_feast.py

# Update ConfigMap
kubectl set env deployment/ml-inference \
  MODEL_NAME=churn_predictor_feast_v2 \
  MODEL_VERSION=1 \
  -n ml-inference

# Restart deployment
kubectl rollout restart deployment/ml-inference -n ml-inference
```

### Update Docker Image

```bash
# Build new image
export IMAGE_TAG="v2.0"
docker build -f ml_deployment/Dockerfile.inference \
  -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ml-inference:${IMAGE_TAG} .

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ml-inference:${IMAGE_TAG}

# Update deployment
kubectl set image deployment/ml-inference \
  inference=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ml-inference:${IMAGE_TAG} \
  -n ml-inference

# Watch rollout
kubectl rollout status deployment/ml-inference -n ml-inference
```

## 🐛 Troubleshooting

### Issue: Pods Not Starting

```bash
# Check pod status
kubectl describe pod -n ml-inference <pod-name>

# Check events
kubectl get events -n ml-inference --sort-by='.lastTimestamp'

# Common fixes:
# 1. Check ECR credentials
kubectl get secret aws-credentials -n ml-inference -o yaml

# 2. Check image pull
kubectl logs -n ml-inference <pod-name> --previous
```

### Issue: Model Not Loading

```bash
# Check logs
kubectl logs -n ml-inference -l app=ml-inference --tail=100

# Verify MLflow connectivity
kubectl exec -n ml-inference <pod-name> -- \
  curl http://mlflow-service.asgard.svc.cluster.local:5000/health

# Verify model exists
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
curl http://localhost:5000/api/2.0/mlflow/registered-models/get?name=churn_predictor_feast
```

### Issue: Inference Errors

```bash
# Check feature names
curl http://localhost:8080/metadata | jq '.feature_names'

# Ensure input features match model features
# Missing features will cause prediction errors
```

## 🔒 Security Best Practices

1. **Use IRSA (IAM Roles for Service Accounts)**

   ```yaml
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ml-inference-role
   ```

2. **Enable TLS**

   - Use cert-manager for automatic certificates
   - Configure ingress with TLS

3. **Network Policies**

   ```bash
   kubectl apply -f ml_deployment/k8s/network-policy.yaml
   ```

4. **Resource Limits**
   - Already configured in deployment.yaml
   - Prevents resource exhaustion

## 📈 Scaling

### Manual Scaling

```bash
# Scale replicas
kubectl scale deployment ml-inference --replicas=5 -n ml-inference
```

### Auto-scaling (HPA)

Already configured in `deployment.yaml`:

- Min replicas: 2
- Max replicas: 10
- CPU threshold: 70%
- Memory threshold: 80%

## 📝 Environment Variables

| Variable              | Description           | Default                      |
| --------------------- | --------------------- | ---------------------------- |
| `MLFLOW_TRACKING_URI` | MLflow server URL     | `http://mlflow-service:5000` |
| `MODEL_NAME`          | Model name to load    | `churn_predictor_feast`      |
| `MODEL_VERSION`       | Model version         | `latest`                     |
| `PORT`                | Service port          | `8080`                       |
| `AWS_REGION`          | AWS region            | `eu-north-1`                 |
| `FEAST_REPO_PATH`     | Feast repository path | `/tmp/feast_repo`            |

## 🎯 Production Checklist

- [ ] Train model with production data
- [ ] Test model performance
- [ ] Build and test Docker image locally
- [ ] Push image to ECR
- [ ] Configure ingress hostname
- [ ] Set up DNS records
- [ ] Create TLS certificates
- [ ] Deploy to staging environment
- [ ] Run integration tests
- [ ] Deploy to production
- [ ] Set up monitoring alerts
- [ ] Document API endpoints
- [ ] Create runbooks

## 📞 Support

For issues or questions:

1. Check logs: `kubectl logs -n ml-inference -l app=ml-inference`
2. Review MLflow UI: http://localhost:5000
3. Check deployment status: `kubectl describe deployment ml-inference -n ml-inference`

---

**Last Updated:** November 6, 2025  
**Version:** 1.0.0  
**Author:** Asgard Platform Team
