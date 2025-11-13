# MLOps Deploy API - Test Results and Fix

## 🔍 Issue Identified

When testing the `/mlops/deploy` API endpoint, the deployment fails during the training phase with the following error:

```
mlflow.exceptions.MlflowException: API request to endpoint /api/2.0/mlflow/logged-models failed with error code 404
```

### Root Cause

**MLflow Version Incompatibility:**

- The application uses **MLflow 2.16.2** (client)
- The MLflow tracking server doesn't support the `/api/2.0/mlflow/logged-models` endpoint
- This endpoint is part of a newer MLflow feature for logged models tracking
- The older MLflow server (likely v2.x < 2.14) doesn't have this endpoint

### Error Flow

1. User uploads training script with `mlflow.sklearn.log_model(model, 'model')`
2. Script executes successfully and creates MLflow run
3. When logging the model, MLflow client tries to call `/api/2.0/mlflow/logged-models`
4. MLflow server returns 404 (endpoint doesn't exist)
5. Training fails and deployment aborts

## ✅ Solution Implemented

### Code Changes in `app/mlops/service.py`

**1. Disable Logged Models Feature**

Added environment variables to disable the incompatible features:

```python
# In _run_training_sync method
injected_script = f"""
import os
import mlflow

os.environ['MLFLOW_TRACKING_URI'] = '{self.mlflow_tracking_uri}'
os.environ['MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING'] = 'false'
os.environ['MLFLOW_ENABLE_PROXY_MLMODEL_ARTIFACT_LOGGING'] = 'false'
mlflow.set_tracking_uri('{self.mlflow_tracking_uri}')
"""

# Also set in subprocess environment
env = os.environ.copy()
env["MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING"] = "false"
env["MLFLOW_ENABLE_PROXY_MLMODEL_ARTIFACT_LOGGING"] = "false"
```

**2. Improved Error Messages**

Changed HTTPException detail from dict to string for proper error reporting:

```python
except Exception as training_error:
    full_error_msg = (
        f"Training Failed\n\n"
        f"Error: {str(training_error)}\n\n"
        f"Traceback:\n{error_detail}"
    )
    raise HTTPException(status_code=500, detail=full_error_msg)
```

**3. Added Debug Logging**

Added more detailed logging to track script decoding and execution:

```python
print(f"🔍 Attempting to decode script_content (length: {len(request.script_content)})")
print(f"✅ Script decoded from base64 (decoded length: {len(script_text)})")
print(f"📝 Script preview (first 200 chars):\n{script_text[:200]}...")
```

## 🚀 Deployment Required

### To Apply the Fix

The changes are in the code but need to be deployed via Docker image:

```bash
# Build new image
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .

# Push to ECR
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin \
  637423187518.dkr.ecr.eu-north-1.amazonaws.com

docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest

# Restart deployment
kubectl rollout restart deployment/asgard-app -n asgard
kubectl rollout status deployment/asgard-app -n asgard
```

## 🧪 Testing After Fix

Once deployed, test with:

```bash
# Test with the provided test script
python ml_deployment/test_deployment.py --api-url http://localhost:8080

# Or manual test
curl -X POST "http://localhost:8080/mlops/deploy" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_deploy_request.json
```

## 📋 Alternative Solutions

### Option 1: Upgrade MLflow Server (Recommended)

Upgrade the MLflow tracking server to match the client version (2.16.2):

```bash
# Update MLflow server deployment
kubectl set image deployment/mlflow -n asgard \
  mlflow=ghcr.io/mlflow/mlflow:v2.16.2
```

### Option 2: Downgrade MLflow Client

Downgrade the client in `pyproject.toml`:

```toml
[project.dependencies]
mlflow = "~=2.13.0"  # Use older version
```

### Option 3: Use Environment Variable (Current Fix)

The current fix uses environment variables to disable incompatible features, which is the quickest solution that doesn't require infrastructure changes.

## 📊 Test Results

### Before Fix

```
Status: FAILED
Error: API request to /api/2.0/mlflow/logged-models failed with 404
Training: Completed but model logging failed
Deployment: Aborted
```

### After Fix (Expected)

```
Status: SUCCESS
Training: Completed ✅
Model Logged: ✅
Docker Build: ✅
ECR Push: ✅
K8s Deploy: ✅
Inference URL: http://X.X.X.X
```

## 🔗 Related Files

- `app/mlops/service.py` - Main fix location
- `ml_deployment/test_deployment.py` - Test script
- `docs/MLOPS_DEPLOY_API_GUIDE.md` - API documentation
- `docs/EXAMPLE_TRAINING_SCRIPT.md` - Training script examples

## ⚠️ Note

The fix has been applied to the source code but requires Docker image rebuild and redeployment to take effect in the running Kubernetes cluster.

## 📝 Summary

**Issue:** MLflow client/server version mismatch causing 404 errors  
**Fix:** Disable incompatible features via environment variables  
**Status:** Code updated, awaiting Docker rebuild and deployment  
**Impact:** Will allow training scripts to execute and models to be deployed successfully
