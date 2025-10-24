# MLflow Dashboard Empty - Diagnosis & Solution

## 🔍 Root Cause Analysis

Your MLflow dashboard is empty because:

### ✅ What's Working

1. **MLflow pod is running** (46h uptime)
2. **PostgreSQL is running** and accessible
3. **Database schema is properly initialized** (19 tables created)
4. **Default experiment exists** (count: 1)

### ❌ What's the Problem

1. **No training runs** - Database shows 0 runs
2. **No registered models** - Database shows 0 models
3. **Worker timeout warnings** - MLflow workers are timing out (performance issue)

## 📊 Current Status

```bash
# Database Status
Experiments: 1 (default only)
Runs: 0
Registered Models: 0
```

**The dashboard is empty because no ML experiments have been run yet!**

## 🎯 Solution: Create Test Experiments

### Option 1: Quick Test via Python Script

Create a test script to verify MLflow is working:

```python
# test_mlflow.py
import mlflow
import os

# Set MLflow tracking URI
mlflow.set_tracking_uri("http://mlflow-service.asgard.svc.cluster.local:5000")

# Create an experiment
experiment_name = "test_experiment"
mlflow.set_experiment(experiment_name)

# Start a run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_param("batch_size", 32)

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("loss", 0.05)

    # Log model (simple example)
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=10)
    mlflow.sklearn.log_model(model, "model")

print("✅ Test experiment logged successfully!")
```

Run from a pod in the same namespace:

```bash
kubectl run -n asgard mlflow-test --image=python:3.10-slim -it --rm -- bash
pip install mlflow scikit-learn boto3 psycopg2-binary
python test_mlflow.py
```

### Option 2: Use Your Existing MLOps API

Since you have the MLOps API, you can use it to train models:

```bash
# From your application pod or local machine (with port-forward)
curl -X POST http://localhost:8000/mlops/models \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_name": "test_churn_prediction",
    "model_name": "test_model",
    "framework": "sklearn",
    "model_type": "classification",
    "data_source": {
      "feature_views": ["customer_features"],
      "entities": {"customer_id": [1, 2, 3, 4, 5]},
      "target_column": "churned"
    },
    "hyperparameters": {
      "params": {
        "n_estimators": 100,
        "max_depth": 10
      }
    }
  }'
```

### Option 3: Port Forward and Test Locally

```bash
# 1. Port forward MLflow service
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# 2. In another terminal, set environment variable
export MLFLOW_TRACKING_URI=http://localhost:5000

# 3. Run Python script
python test_mlflow.py
```

## 🔧 Performance Issue: Worker Timeouts

Your logs show worker timeouts. This can affect dashboard responsiveness.

### Current Issue in Logs:

```
[CRITICAL] WORKER TIMEOUT (pid:175)
```

### Solution: Increase Worker Timeout

Update the MLflow deployment to increase gunicorn worker timeout:

```yaml
# mlflow/mlflow-deployment.yaml
command:
  - /bin/bash
  - -c
  - |
    pip install --no-cache-dir mlflow==2.16.2 psycopg2-binary boto3 && \
    mlflow server \
      --host=0.0.0.0 \
      --port=5000 \
      --backend-store-uri=${MLFLOW_BACKEND_STORE_URI} \
      --default-artifact-root=${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
      --serve-artifacts \
      --gunicorn-opts="--timeout 120 --workers 2"
```

Apply the change:

```bash
kubectl apply -f mlflow/mlflow-deployment.yaml
kubectl rollout restart -n asgard deployment/mlflow-deployment
```

## 📝 Verification Steps

After creating test experiments:

### 1. Check Database

```bash
# Verify runs were created
kubectl exec -n asgard postgres-deployment-b776c57d4-hjs4d -- \
  psql -U mlflow -d mlflow -c "SELECT COUNT(*) FROM runs;"

# Check experiments
kubectl exec -n asgard postgres-deployment-b776c57d4-hjs4d -- \
  psql -U mlflow -d mlflow -c "SELECT name FROM experiments;"
```

### 2. Check MLflow Dashboard

```bash
# Port forward
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# Open browser
http://localhost:5000
```

### 3. Test API Connection

```bash
# From inside cluster
kubectl run -n asgard test-curl --image=curlimages/curl -it --rm -- \
  curl http://mlflow-service:5000/api/2.0/mlflow/experiments/list
```

## 🎯 Quick Fix Summary

**The dashboard is empty because no experiments have been run yet!**

To fix:

1. ✅ MLflow is running correctly
2. ✅ Database is working
3. ⚠️ Fix worker timeouts (optional but recommended)
4. ❗ **Run some ML experiments** to populate the dashboard

### Minimal Test Command

```bash
# Port forward MLflow
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# Install MLflow locally
pip install mlflow

# Create test experiment
export MLFLOW_TRACKING_URI=http://localhost:5000
mlflow experiments create -n "my_first_experiment"

# Or use Python
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
mlflow.set_experiment('test')
with mlflow.start_run():
    mlflow.log_metric('test', 1.0)
print('✅ Done!')
"
```

## 🔍 Troubleshooting

### If dashboard still shows nothing:

1. **Check browser console** for JavaScript errors
2. **Clear browser cache**
3. **Check MLflow logs** for errors:

   ```bash
   kubectl logs -n asgard -l app=mlflow --tail=100
   ```

4. **Verify service is accessible**:

   ```bash
   kubectl exec -n asgard -it mlflow-deployment-854ccdc8b9-rwjf2 -- \
     wget -O- http://localhost:5000/api/2.0/mlflow/experiments/list
   ```

5. **Check S3 connectivity** (for artifacts):
   ```bash
   kubectl exec -n asgard postgres-deployment-b776c57d4-hjs4d -- \
     psql -U mlflow -d mlflow -c "SELECT artifact_location FROM experiments;"
   ```

## 📋 Summary

| Component       | Status         | Issue                          |
| --------------- | -------------- | ------------------------------ |
| MLflow Pod      | ✅ Running     | Minor: Worker timeouts         |
| PostgreSQL      | ✅ Running     | No issues                      |
| Database Schema | ✅ Initialized | 19 tables created              |
| Experiments     | ⚠️ Empty       | **No runs logged yet**         |
| Dashboard       | ⚠️ Empty       | **Expected - no data to show** |

**Next Step**: Run ML experiments using any of the three options above!

---

**Date**: October 17, 2025  
**Issue**: Dashboard empty (expected - no experiments run)  
**Solution**: Log some experiments/runs to populate the dashboard
