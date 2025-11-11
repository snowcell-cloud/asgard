# Quick Reference - ML Deployment Testing

## Current Status (2025-11-07)

### ✅ What's Working

- Training pipeline via `/mlops/training/upload` API
- Model registration in MLflow Model Registry
- Feast feature store integration
- MLflow tracking and metrics

### ⚠️ What Needs Work

- Automated deployment (service code needs update)
- ECR push timing out
- Deployment to K8s not triggered automatically

## Quick Commands

### Setup Port-Forward

```bash
nohup kubectl port-forward -n asgard svc/asgard-app 8000:80 </dev/null >/tmp/pf-asgard.log 2>&1 & echo $!
```

### Fix Feast Configuration

```bash
kubectl exec -n asgard deployment/asgard-app -- bash -c 'cat > /tmp/feast_repo/feature_store.yaml << "EOF"
project: asgard_features
registry: /tmp/feast_repo/registry.db
provider: local
offline_store:
    type: file
entity_key_serialization_version: 2
EOF'
```

### Test Complete Workflow

```bash
cd /home/hac/downloads/code/asgard-dev
python3 test_deployment.py
```

### Check API Status

```bash
curl http://localhost:8000/mlops/status | python3 -m json.tool
```

### List Training Jobs

```bash
curl http://localhost:8000/mlops/training/jobs | python3 -m json.tool
```

### Get Specific Job

```bash
JOB_ID="<job-id>"
curl http://localhost:8000/mlops/training/jobs/$JOB_ID | python3 -m json.tool
```

### Get Model Info

```bash
curl http://localhost:8000/mlops/models/test_model_feast | python3 -m json.tool
```

### Manual Deploy (if automated fails)

```bash
python3 manual_deploy.py
```

### Check EKS Deployments

```bash
kubectl get deployments -n asgard
kubectl get pods -n asgard
kubectl get svc -n asgard
```

### Test Inference (when deployed)

```bash
MODEL_NAME="test_model_feast"
kubectl port-forward -n asgard svc/${MODEL_NAME}-inference 8080:80 &
sleep 3

# Health check
curl http://localhost:8080/health

# Metadata
curl http://localhost:8080/metadata

# Prediction
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

## Error Fixes

### Error: "Extra inputs are not permitted [region]"

**Cause**: Feast configuration has invalid parameters

**Fix**: Run the "Fix Feast Configuration" command above

### Error: "API request to /api/2.0/mlflow/logged-models failed"

**Cause**: MLflow API version incompatibility

**Fix**: Already fixed in `ml_deployment/train_with_feast.py` - model registration now uses compatible API

### Error: "No MLflow run created"

**Cause**: Service can't find run in expected experiment

**Fix**: Ensured EXPERIMENT_NAME environment variable is passed in test script

### Error: "model_version: null" in job status

**Cause**: Service tries to register already-registered model

**Impact**: Not critical - model IS registered by training script, deployment service just doesn't know the version

**Fix**: Requires service.py update (needs image rebuild)

## Files to Know

### Key Scripts

- `test_deployment.py` - Complete end-to-end test
- `manual_deploy.py` - Manual deployment workflow
- `ml_deployment/train_with_feast.py` - Training script (upload this via API)
- `ml_deployment/inference_service.py` - FastAPI inference service

### Configuration

- Feast config: `/tmp/feast_repo/feature_store.yaml` (in pod)
- MLflow: `http://mlflow-service.asgard.svc.cluster.local:5000`
- ECR: `637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model`
- Namespace: `asgard`

### Documentation

- `TESTING_SUMMARY.md` - Complete test results and findings
- `ml_deployment/INTEGRATION_GUIDE.md` - Integration documentation
- `ml_deployment/COMPLETE_INTEGRATION.md` - Architecture guide

## Sample Training Request

```python
import base64
import requests

# Read training script
with open("ml_deployment/train_with_feast.py", "rb") as f:
    script_content = base64.b64encode(f.read()).decode('utf-8')

# Prepare request
payload = {
    "script_name": "train_with_feast.py",
    "script_content": script_content,
    "experiment_name": "my_experiment",
    "model_name": "my_model",
    "requirements": ["scikit-learn", "pandas", "numpy"],
    "environment_vars": {
        "USE_FEAST": "false",  # or "true" to use Feast
        "MODEL_NAME": "my_model",
        "EXPERIMENT_NAME": "my_experiment"
    },
    "timeout": 300,
    "tags": {
        "version": "1.0",
        "type": "classifier"
    }
}

# Submit
response = requests.post(
    "http://localhost:8000/mlops/training/upload",
    json=payload
)

print(response.json())
```

## Troubleshooting

### Port-forward not working

```bash
# Kill existing
pkill -f "port-forward.*asgard-app"

# Restart
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# Test
curl http://localhost:8000/mlops/status
```

### Pod not ready

```bash
# Check status
kubectl get pods -n asgard

# Check logs
kubectl logs -n asgard deployment/asgard-app --tail=50

# Restart if needed
kubectl rollout restart deployment asgard-app -n asgard
```

### MLflow not accessible

```bash
# Check MLflow pod
kubectl get pods -n asgard | grep mlflow

# Check service
kubectl get svc -n asgard | grep mlflow

# Port-forward to MLflow UI
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
# Then visit http://localhost:5000
```

### Training job stuck

```bash
# Get job logs
JOB_ID="<job-id>"
curl http://localhost:8000/mlops/training/jobs/$JOB_ID | python3 -c "import sys, json; print(json.load(sys.stdin)['logs'])"
```

## Performance Notes

### Training Time

- Synthetic data (1000 samples): ~6-8 seconds
- Includes: requirements install, training, model registration

### Image Build Time

- Docker build: ~30-60 seconds
- Docker push to ECR: Variable (network dependent)

### Deployment Time

- K8s deployment apply: ~5-10 seconds
- Pod startup: ~20-30 seconds
- Total: ~30-40 seconds
