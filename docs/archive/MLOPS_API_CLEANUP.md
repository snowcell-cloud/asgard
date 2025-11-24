# MLOps API Cleanup - Inference Separation

**Date**: November 12, 2025  
**Change Type**: API Reorganization

---

## 🎯 Summary

Removed inference endpoint from MLOps service. **Model inference is now exclusively done via deployed model URLs**, not through the main MLOps API.

---

## ❌ Removed Endpoints

### `POST /mlops/inference` - REMOVED

**Reason for Removal:**

- ❌ Redundant - Each deployed model already has `/predict` endpoint
- ❌ Inefficient - Loads models into main service (resource waste)
- ❌ Not scalable - Single service handles all inference
- ❌ Poor isolation - Models share resources
- ❌ Maintenance burden - Need to keep models loaded

**Previous Behavior:**

```bash
# OLD - No longer available
curl -X POST http://localhost:8000/mlops/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "my_model",
    "model_version": "1",
    "inputs": {
      "feature1": [1, 2, 3]
    }
  }'
```

---

## ✅ Current API Structure

### MLOps Service (Management Only)

**Purpose**: Model lifecycle management and orchestration

**Endpoints:**

| Endpoint                        | Method | Purpose                 |
| ------------------------------- | ------ | ----------------------- |
| `/mlops/training/upload`        | POST   | Upload training script  |
| `/mlops/training/jobs/{job_id}` | GET    | Check training status   |
| `/mlops/deploy`                 | POST   | One-click deployment    |
| `/mlops/deployments/{job_id}`   | GET    | Check deployment status |
| `/mlops/registry`               | POST   | Register model manually |
| `/mlops/models`                 | GET    | List all models         |
| `/mlops/models/{model_name}`    | GET    | Get model info          |
| `/mlops/status`                 | GET    | Platform status         |

---

## 🚀 How to Use Inference Now

### Step 1: Deploy a Model

```bash
curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train.py",
    "script_content": "..."  ,
    "experiment_name": "production",
    "model_name": "my_model",
    "requirements": ["scikit-learn"],
    "replicas": 2,
    "namespace": "asgard"
  }'
```

**Response:**

```json
{
  "job_id": "a3b4c5d6",
  "model_name": "my_model",
  "status": "training",
  "message": "Deployment started. Use /mlops/deployments/a3b4c5d6 to check status"
}
```

### Step 2: Check Deployment Status

```bash
curl http://localhost:8000/mlops/deployments/a3b4c5d6
```

**Response (when deployed):**

```json
{
  "job_id": "a3b4c5d6",
  "status": "deployed",
  "deployment_url": "http://51.89.136.142",
  "external_ip": "51.89.136.142",
  "model_version": "1",
  "run_id": "abc123...",
  "ecr_image": "637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard-model:my-model-v1",
  "duration_seconds": 180
}
```

### Step 3: Use Deployed Model for Inference

#### Health Check

```bash
curl http://51.89.136.142/health
```

**Response:**

```json
{
  "status": "healthy",
  "model": {
    "name": "my_model",
    "version": "1",
    "run_id": "abc123..."
  }
}
```

#### Get Metadata

```bash
curl http://51.89.136.142/metadata
```

**Response:**

```json
{
  "model_name": "my_model",
  "model_version": "1",
  "run_id": "abc123...",
  "mlflow_uri": "http://mlflow-service.asgard.svc.cluster.local:5000",
  "model_loaded": true
}
```

#### Make Predictions ⭐

```bash
curl -X POST http://51.89.136.142/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "feature1": [1, 2, 3],
      "feature2": [4, 5, 6]
    }
  }'
```

**Response:**

```json
{
  "predictions": [0, 1, 1]
}
```

---

## 🎯 Benefits of This Approach

### 1. **Better Scalability**

- Each model can be scaled independently
- Horizontal scaling with K8s replicas
- Load balancing across pods

```bash
# Scale a specific model
kubectl scale deployment my-model-inference -n asgard --replicas=5
```

### 2. **Resource Isolation**

- Models don't share resources
- One model's high load doesn't affect others
- Better resource allocation

### 3. **Independent Versioning**

- Deploy multiple versions simultaneously
- A/B testing between versions
- Gradual rollout

```bash
# Version 1 at http://ip1/predict
# Version 2 at http://ip2/predict
```

### 4. **Fault Isolation**

- One model crash doesn't affect others
- Better error handling per model
- Independent health monitoring

### 5. **Optimized Performance**

- Model loaded once at startup
- No cold start for each request
- Dedicated resources per model

### 6. **Easier Monitoring**

- Per-model metrics
- Separate logs per deployment
- Individual health checks

---

## 📊 Architecture Comparison

### Old Architecture (Single Service)

```
┌─────────────────────────────────────┐
│     MLOps Service (Port 8000)       │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  /mlops/training            │   │
│  │  /mlops/deploy              │   │
│  │  /mlops/inference ❌        │   │  ← BAD: All models here
│  │                             │   │
│  │  Model Cache:               │   │
│  │  - model_1 (1GB)            │   │
│  │  - model_2 (800MB)          │   │
│  │  - model_3 (1.2GB)          │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### New Architecture (Separated)

```
┌─────────────────────────────────────┐
│   MLOps Service (Port 8000)         │
│   Management Only ✅                │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  /mlops/training            │   │
│  │  /mlops/deploy              │   │
│  │  /mlops/models              │   │
│  │  /mlops/deployments         │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
                 │
                 │ Deploys to →
                 ↓
┌─────────────────────────────────────────────────────────┐
│              Kubernetes Cluster                         │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │  Model 1 Service │  │  Model 2 Service │           │
│  │  http://IP1      │  │  http://IP2      │  ...      │
│  │                  │  │                  │           │
│  │  GET /health     │  │  GET /health     │           │
│  │  GET /metadata   │  │  GET /metadata   │           │
│  │  POST /predict✅ │  │  POST /predict✅ │           │
│  │                  │  │                  │           │
│  │  Replicas: 2     │  │  Replicas: 3     │           │
│  └──────────────────┘  └──────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Migration Guide

### If You Were Using `/mlops/inference`

**Old Code:**

```python
import requests

# ❌ OLD - No longer works
response = requests.post(
    "http://localhost:8000/mlops/inference",
    json={
        "model_name": "my_model",
        "model_version": "1",
        "inputs": {
            "feature1": [1, 2, 3]
        }
    }
)
predictions = response.json()["predictions"]
```

**New Code:**

```python
import requests

# ✅ NEW - Use deployed model URL

# Step 1: Get deployment URL (one time)
deployment_status = requests.get(
    "http://localhost:8000/mlops/deployments/a3b4c5d6"
).json()
model_url = deployment_status["deployment_url"]  # http://51.89.136.142

# Step 2: Use model URL for inference
response = requests.post(
    f"{model_url}/predict",
    json={
        "inputs": {
            "feature1": [1, 2, 3]
        }
    }
)
predictions = response.json()["predictions"]
```

**Better: Cache the model URL**

```python
# Store deployment_url in config/database
MODEL_URLS = {
    "my_model": "http://51.89.136.142",
    "another_model": "http://51.89.136.143",
}

# Use it
response = requests.post(
    f"{MODEL_URLS['my_model']}/predict",
    json={"inputs": {...}}
)
```

---

## 📝 Updated Workflows

### Workflow 1: Train and Deploy

```bash
# 1. Deploy model (trains automatically)
curl -X POST http://localhost:8000/mlops/deploy \
  -d '{"script_name": "train.py", "script_content": "...", ...}'

# Response: {"job_id": "abc123"}

# 2. Wait and check status
curl http://localhost:8000/mlops/deployments/abc123

# Response: {"status": "deployed", "deployment_url": "http://IP"}

# 3. Use deployed model
curl -X POST http://IP/predict -d '{"inputs": {...}}'
```

### Workflow 2: List Available Models

```bash
# Get all deployed models from K8s
kubectl get services -n asgard -l app.kubernetes.io/component=inference

# Or via MLOps API (registry only, not deployed services)
curl http://localhost:8000/mlops/models
```

### Workflow 3: Update a Model

```bash
# 1. Deploy new version
curl -X POST http://localhost:8000/mlops/deploy \
  -d '{"model_name": "my_model", ...}'

# This creates a NEW deployment with a new IP
# Response: {"job_id": "def456"}

# 2. Get new deployment URL
curl http://localhost:8000/mlops/deployments/def456
# Response: {"deployment_url": "http://NEW_IP"}

# 3. Update your application to use new URL
# Or use traffic splitting for A/B testing
```

---

## 🛠️ Code Changes

### Files Modified

1. **`app/mlops/router.py`**

   - Removed: `@router.post("/inference")`
   - Removed: `InferenceRequest`, `InferenceResponse` imports
   - Updated: Documentation for `/deploy` endpoint

2. **`app/mlops/service.py`**

   - Removed: `async def inference()`
   - Removed: `self.model_cache`
   - Removed: `InferenceRequest`, `InferenceResponse` imports
   - Removed: `_load_model()` method (if exists)

3. **`app/mlops/schemas.py`**
   - No changes (kept InferenceRequest/Response for reference)

---

## ⚠️ Breaking Changes

### What Breaks

1. **Direct inference calls to MLOps service**

   ```bash
   # ❌ This will return 404
   curl -X POST http://localhost:8000/mlops/inference
   ```

2. **Code expecting InferenceResponse from MLOps**
   ```python
   # ❌ This endpoint no longer exists
   response = mlops_client.post("/mlops/inference", ...)
   ```

### What Still Works

1. ✅ Training via `/mlops/training/upload`
2. ✅ Deployment via `/mlops/deploy`
3. ✅ Model registry via `/mlops/models`
4. ✅ All deployed model inference endpoints

---

## 🧪 Testing

### Test Deployed Model

```bash
# 1. Deploy
JOB_ID=$(curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{"script_name": "test.py", ...}' | jq -r '.job_id')

# 2. Wait for deployment
while true; do
  STATUS=$(curl -s http://localhost:8000/mlops/deployments/$JOB_ID | jq -r '.status')
  echo "Status: $STATUS"
  [ "$STATUS" = "deployed" ] && break
  sleep 10
done

# 3. Get URL
MODEL_URL=$(curl -s http://localhost:8000/mlops/deployments/$JOB_ID | jq -r '.deployment_url')
echo "Model URL: $MODEL_URL"

# 4. Test inference
curl -X POST $MODEL_URL/predict \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"feature1": [1, 2, 3]}}'
```

---

## 📈 Performance Impact

### Before (Single Service)

- ❌ All models loaded in one service
- ❌ Memory: ~3GB for 3 models
- ❌ Request time: Variable (depends on cache)
- ❌ Scaling: Scale entire service with all models

### After (Distributed)

- ✅ Each model in separate pod
- ✅ Memory: 1GB per model (isolated)
- ✅ Request time: Consistent (model always loaded)
- ✅ Scaling: Scale each model independently

---

## 🔍 Monitoring

### Check Deployed Models

```bash
# List all inference services
kubectl get svc -n asgard -l app.kubernetes.io/component=inference

# Get specific model status
kubectl get pods -n asgard -l app=my-model-inference

# View logs
kubectl logs -n asgard -l app=my-model-inference --tail=50

# Check resource usage
kubectl top pods -n asgard -l app=my-model-inference
```

---

## 📚 Related Documentation

- **ONE_CLICK_DEPLOYMENT.md** - Complete deployment guide
- **API_TESTING_GUIDE.md** - API testing examples
- **ARCHITECTURE.md** - System architecture

---

## ✅ Checklist for Teams

### For ML Engineers

- [ ] Update training scripts to use `/mlops/deploy`
- [ ] Store deployment URLs in configuration
- [ ] Update monitoring dashboards for per-model metrics
- [ ] Test model deployment end-to-end

### For Backend Developers

- [ ] Remove `/mlops/inference` calls
- [ ] Update to use deployed model URLs
- [ ] Implement URL caching/configuration
- [ ] Add health checks for model endpoints

### For DevOps

- [ ] Monitor K8s deployments per model
- [ ] Set up alerts for model health
- [ ] Configure auto-scaling per model
- [ ] Document LoadBalancer IPs

---

## 🎯 Summary

**What Changed:**

- ❌ Removed `/mlops/inference` endpoint
- ✅ Inference only via deployed model URLs

**Why:**

- Better scalability
- Resource isolation
- Independent scaling
- Fault isolation
- Improved performance

**How to Adapt:**

1. Deploy models via `/mlops/deploy`
2. Get `deployment_url` from `/mlops/deployments/{job_id}`
3. Use `{deployment_url}/predict` for inference

**Benefits:**

- 🚀 Better performance
- 📈 Easier scaling
- 🔒 Better isolation
- 📊 Clearer metrics
- 🛡️ Fault tolerance

---

**Questions?** Check the updated API documentation at `/docs` endpoint.
