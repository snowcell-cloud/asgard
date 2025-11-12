# 🎯 MLOps API Quick Reference

## ✅ Available Endpoints

### Management APIs (http://localhost:8000/mlops)

| Endpoint                  | Method | Purpose                                | Returns                       |
| ------------------------- | ------ | -------------------------------------- | ----------------------------- |
| `/training/upload`        | POST   | Upload training script                 | `job_id`                      |
| `/training/jobs/{job_id}` | GET    | Training status                        | Status, logs, model version   |
| `/deploy`                 | POST   | Deploy model (train→build→push→deploy) | `job_id`                      |
| `/deployments/{job_id}`   | GET    | Deployment status                      | Status, **deployment_url** ⭐ |
| `/models`                 | GET    | List all models                        | Model list                    |
| `/models/{name}`          | GET    | Get model details                      | Model info                    |
| `/registry`               | POST   | Register model manually                | Model version                 |
| `/status`                 | GET    | Platform health                        | MLflow, Feast status          |

### Inference APIs (on deployed model URL)

| Endpoint    | Method | Purpose          | Example                                     |
| ----------- | ------ | ---------------- | ------------------------------------------- |
| `/health`   | GET    | Health check     | `curl http://IP/health`                     |
| `/metadata` | GET    | Model info       | `curl http://IP/metadata`                   |
| `/predict`  | POST   | Make predictions | `curl -X POST http://IP/predict -d '{...}'` |
| `/`         | GET    | API info         | `curl http://IP/`                           |

---

## ❌ Removed Endpoints

| Endpoint           | Status     | Use Instead                    |
| ------------------ | ---------- | ------------------------------ |
| `/mlops/inference` | ❌ REMOVED | Use `{deployment_url}/predict` |

---

## 🚀 Common Workflows

### Deploy and Use a Model

```bash
# 1. Deploy
curl -X POST http://localhost:8000/mlops/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train.py",
    "script_content": "...",
    "experiment_name": "production",
    "model_name": "my_model",
    "requirements": ["scikit-learn"],
    "replicas": 2
  }'

# Returns: {"job_id": "abc123", "status": "training"}

# 2. Check status (poll until "deployed")
curl http://localhost:8000/mlops/deployments/abc123

# Returns: {
#   "status": "deployed",
#   "deployment_url": "http://51.89.136.142",  ← USE THIS!
#   "model_version": "1"
# }

# 3. Make predictions
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

## 📋 Deployment Statuses

| Status      | Description                | Action             |
| ----------- | -------------------------- | ------------------ |
| `training`  | Model training in progress | Wait               |
| `building`  | Building Docker image      | Wait               |
| `pushing`   | Pushing to ECR             | Wait               |
| `deploying` | Deploying to K8s           | Wait               |
| `deployed`  | ✅ Ready for inference     | Use deployment_url |
| `failed`    | ❌ Error occurred          | Check error field  |

---

## 🎯 Key Points

1. **Management** = `http://localhost:8000/mlops/*`
2. **Inference** = `http://{deployment_url}/predict`
3. **No more** `/mlops/inference` endpoint
4. Each model gets its own URL
5. Models scale independently

---

## 💡 Tips

### Save Deployment URLs

```python
# In your config/database
MODEL_URLS = {
    "churn_model": "http://51.89.136.142",
    "fraud_model": "http://51.89.136.143",
}

# Use them
requests.post(f"{MODEL_URLS['churn_model']}/predict", ...)
```

### Health Monitoring

```bash
# Check if model is healthy
curl http://IP/health

# Get model metadata
curl http://IP/metadata
```

### List Deployed Models

```bash
# Via Kubernetes
kubectl get svc -n asgard -l app.kubernetes.io/component=inference

# Via MLOps (registry only)
curl http://localhost:8000/mlops/models
```

---

## 📖 Full Documentation

- **docs/MLOPS_API_CLEANUP.md** - Complete migration guide
- **ONE_CLICK_DEPLOYMENT.md** - Deployment details
- **API_TESTING_GUIDE.md** - Testing examples

---

**Remember**: Inference happens on deployed model URLs, not on the MLOps service! 🚀
