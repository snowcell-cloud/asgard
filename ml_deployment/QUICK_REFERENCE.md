# ML Deployment - Quick Reference Card

## 🚀 One-Command Deployment

```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="eu-north-1"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

./ml_deployment/deploy.sh
```

## 📋 Common Commands

### Training

```bash
# Via MLOps API
curl -X POST http://localhost:8000/mlops/training/upload \
  -H "Content-Type: application/json" \
  -d @training_payload.json

# Direct script
python3 ml_deployment/train_with_feast.py
```

### Docker

```bash
# Build
docker build -f ml_deployment/Dockerfile.inference -t ml-inference .

# Run locally
docker run -p 8080:8080 \
  -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" \
  -e MODEL_NAME="churn_predictor_feast" \
  ml-inference
```

### Kubernetes

```bash
# Deploy
kubectl apply -f ml_deployment/k8s/deployment.yaml

# Status
kubectl get all -n ml-inference

# Logs
kubectl logs -n ml-inference -l app=ml-inference -f

# Port-forward
kubectl port-forward -n ml-inference svc/ml-inference-service 8080:80
```

### Inference API

```bash
# Health
curl http://localhost:8080/health

# Metadata
curl http://localhost:8080/metadata

# Predict
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "total_purchases": [10, 25],
      "avg_purchase_value": [50.0, 120.5],
      "days_since_last_purchase": [5, 15],
      "customer_lifetime_value": [500.0, 3000.0],
      "account_age_days": [365, 730],
      "support_tickets_count": [2, 1]
    },
    "return_probabilities": true
  }'
```

## 🔧 Troubleshooting

### Model Not Loading

```bash
kubectl exec -n ml-inference <pod> -- \
  curl http://mlflow-service.asgard.svc.cluster.local:5000/health
```

### Check Logs

```bash
kubectl logs -n ml-inference -l app=ml-inference --tail=100
```

### Restart Deployment

```bash
kubectl rollout restart deployment/ml-inference -n ml-inference
```

### Scale Manually

```bash
kubectl scale deployment/ml-inference --replicas=5 -n ml-inference
```

## 📊 Monitoring

```bash
# Pod metrics
kubectl top pods -n ml-inference

# HPA status
kubectl get hpa -n ml-inference

# Events
kubectl get events -n ml-inference --sort-by='.lastTimestamp'
```

## 🔄 Updates

### Update Model

```bash
kubectl set env deployment/ml-inference \
  MODEL_NAME=new_model \
  MODEL_VERSION=2 \
  -n ml-inference
```

### Update Image

```bash
kubectl set image deployment/ml-inference \
  inference=<ECR_URI>/ml-inference:v2.0 \
  -n ml-inference
```

## 📁 File Structure

```
ml_deployment/
├── train_with_feast.py       # Training script
├── inference_service.py       # FastAPI service
├── requirements.txt           # Python deps
├── Dockerfile.inference       # Container build
├── deploy.sh                  # Automation script
├── demo.py                    # Demo workflow
├── README.md                  # Full documentation
├── DEPLOYMENT_SUMMARY.md      # Complete summary
└── k8s/
    └── deployment.yaml        # K8s manifests
```

## 🌐 URLs

- **MLOps API:** http://localhost:8000/mlops
- **MLflow UI:** http://localhost:5000
- **Inference (local):** http://localhost:8080
- **Inference (prod):** https://ml-inference.yourdomain.com

## 🎯 Environment Variables

```bash
# Training
MLFLOW_TRACKING_URI="http://mlflow-service:5000"
MODEL_NAME="churn_predictor_feast"
EXPERIMENT_NAME="feast_ml_deployment"
FEAST_REPO_PATH="/tmp/feast_repo"

# Inference Service
MLFLOW_TRACKING_URI="http://mlflow-service:5000"
MODEL_NAME="churn_predictor_feast"
MODEL_VERSION="latest"
PORT="8080"

# AWS
AWS_ACCOUNT_ID="123456789012"
AWS_REGION="eu-north-1"
AWS_ACCESS_KEY_ID="your-key"
AWS_SECRET_ACCESS_KEY="your-secret"
```

## 📞 Quick Help

```bash
# Deploy script help
./ml_deployment/deploy.sh --help

# View full docs
cat ml_deployment/README.md

# Run demo
python3 ml_deployment/demo.py
```

---

**Last Updated:** November 6, 2025
