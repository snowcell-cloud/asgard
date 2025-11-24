# 🎯 MLOps API Quick Reference

## ✅ Available Endpoints (Final - 4 Endpoints)

### Management APIs (http://localhost:8000/mlops)

| Endpoint         | Method | Purpose                                | Returns                     |
| ---------------- | ------ | -------------------------------------- | --------------------------- |
| `/deploy`        | POST   | Deploy model (train→build→push→deploy) | Inference URL (synchronous) |
| `/models`        | GET    | List all models                        | Model list                  |
| `/models/{name}` | GET    | Get model details                      | Model info                  |
| `/status`        | GET    | Platform health                        | MLflow, Feast status        |

### Inference APIs (on deployed model URL)

| Endpoint    | Method | Purpose          | Example                                     |
| ----------- | ------ | ---------------- | ------------------------------------------- |
| `/health`   | GET    | Health check     | `curl http://IP/health`                     |
| `/metadata` | GET    | Model info       | `curl http://IP/metadata`                   |
| `/predict`  | POST   | Make predictions | `curl -X POST http://IP/predict -d '{...}'` |
| `/`         | GET    | API info         | `curl http://IP/`                           |

---

## ❌ Removed Endpoints (Streamlined API)

| Endpoint                  | Status     | Use Instead                    |
| ------------------------- | ---------- | ------------------------------ |
| `/mlops/inference`        | ❌ REMOVED | Use `{inference_url}/predict`  |
| `/training/upload`        | ❌ REMOVED | Use `/deploy`                  |
| `/training/jobs/{job_id}` | ❌ REMOVED | `/deploy` is synchronous now   |
| `/registry`               | ❌ REMOVED | Auto-registered in `/deploy`   |
| `/deployments/{job_id}`   | ❌ REMOVED | `/deploy` returns URL directly |

---

## 🚀 Single Workflow: Deploy and Use

```bash
# Deploy (returns inference URL in 3-5 minutes - synchronous)
curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train.py",
    "script_content": "<base64-encoded-script>",
    "experiment_name": "production",
    "model_name": "my_model",
    "requirements": ["scikit-learn==1.3.0"]
    "replicas": 2
  }'

# Response (synchronous - returns in 3-5 minutes):
{
  "deployment_id": "my_model-v1-abc123",
  "model_name": "my_model",
  "model_version": "1",
  "status": "deployed",
  "inference_url": "http://51.89.136.142/predict",
  "endpoints": {
    "predict": "http://51.89.136.142/predict",
    "health": "http://51.89.136.142/health",
    "metadata": "http://51.89.136.142/metadata"
  },
  "deployment_time_seconds": 245.8
}

# Use the model immediately
curl -X POST http://51.89.136.142/predict \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "feature1": [1, 2, 3],
      "feature2": [4, 5, 6]
    }
  }'

# Returns: {"predictions": [0, 1, 1]}
```

---

## 🎯 Key Changes

### Before (8 Endpoints - Complex)

- ❌ Upload training script → Poll for completion
- ❌ Register model manually
- ❌ Deploy model → Poll for completion
- ❌ Use `/mlops/inference` proxy

### After (4 Endpoints - Simple)

- ✅ One `/deploy` call → Returns inference URL
- ✅ Automatic registration
- ✅ Synchronous (no polling)
- ✅ Direct inference URLs

---

## 🎯 Key Points

1. **Management** = `http://localhost:8000/mlops/*` (4 endpoints)
2. **Inference** = `http://{inference_url}/predict` (on deployed URLs)
3. **No polling** - Synchronous deployment
4. **No proxy** - Direct model URLs
5. **One API call** - Complete deployment

---

## 💡 Tips

### Python Client Example

```python
import requests
import base64

# Read and encode script
with open("train.py") as f:
    script = f.read()
script_b64 = base64.b64encode(script.encode()).decode()

# Deploy (synchronous)
response = requests.post(
    "http://localhost:8000/mlops/deploy",
    json={
        "script_content": script_b64,
        "script_name": "train.py",
        "experiment_name": "fraud-detection",
        "model_name": "fraud-model",
        "requirements": ["scikit-learn==1.3.0"]
    }
)

deployment = response.json()
inference_url = deployment["inference_url"]

# Use immediately
result = requests.post(
    inference_url,
    json={"data": [[0.1, 0.2, 0.3, 0.4, 0.5]]}
)
print(result.json())
```

### Save Deployment URLs

```python
# In your config/database
MODEL_URLS = {
    "churn_model": "http://51.89.136.142/predict",
    "fraud_model": "http://51.89.136.143/predict",
}

# Use them
requests.post(MODEL_URLS['churn_model'], ...)
```

### Health Monitoring

```bash
# Check if model is healthy
curl http://51.89.136.142/health

# Get model metadata
curl http://51.89.136.142/metadata
```

### List Models

```bash
# List all registered models
curl http://localhost:8000/mlops/models

# Get specific model details
curl http://localhost:8000/mlops/models/fraud-model

# Check platform health
curl http://localhost:8000/mlops/status
```

---

## 📖 Full Documentation

- **docs/MLOPS_API_FINAL.md** - Complete API reference
- **docs/SINGLE_CLICK_DEPLOYMENT.md** - Deployment guide
- **docs/MLOPS_API_CLEANUP.md** - Migration details
- **docs/API_TESTING_GUIDE.md** - Testing examples

---

## 📊 Improvements

| Metric                   | Before | After | Change |
| ------------------------ | ------ | ----- | ------ |
| Endpoints                | 8      | 4     | -50%   |
| API calls for deployment | 3-5    | 1     | -80%   |
| Polling required         | Yes    | No    | ✅     |
| Response time            | Async  | Sync  | ✅     |
| Code lines               | 990    | 640   | -35%   |

---

**Remember**: Inference happens on deployed model URLs, not on the MLOps service! 🚀
