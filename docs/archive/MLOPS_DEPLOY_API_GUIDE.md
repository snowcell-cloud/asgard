# MLOps Deploy API - Complete Guide

## 🎯 Overview

The `/mlops/deploy` API endpoint provides **single-click deployment** for ML models. Upload your training script, and get back a deployed model with an inference URL - all in one API call.

## 🚀 How It Works

### The Complete Pipeline

```
Upload Script → Train Model → Build Image → Push to ECR → Deploy to K8s → Return URL
   (instant)     (1-2 min)      (1-2 min)     (30 sec)      (1-2 min)      (instant)
```

**Total Time:** ~3-5 minutes (synchronous)

### What Happens Automatically

1. **Training Phase**

   - Your script is decoded (from base64)
   - MLflow configuration is injected
   - Requirements are installed
   - Script executes and trains model
   - Model is registered in MLflow Registry

2. **Build Phase**

   - Multi-stage Dockerfile is created
   - Optimized inference service image is built
   - Image is tagged with model version

3. **Push Phase**

   - AWS ECR authentication
   - Docker image push to registry

4. **Deploy Phase**

   - Kubernetes Deployment created
   - LoadBalancer Service provisioned
   - Health checks configured
   - External IP allocated
   - Deployment verified

5. **Response**
   - Inference URL returned
   - All endpoints provided
   - Ready for immediate use!

## 📝 API Specification

### Endpoint

```
POST /mlops/deploy
```

### Request Schema

```json
{
  "script_name": "string (required)",
  "script_content": "string (required, base64-encoded)",
  "experiment_name": "string (required)",
  "model_name": "string (required)",
  "requirements": ["string", "..."] (optional),
  "environment_vars": {"key": "value"} (optional),
  "timeout": 300 (optional, 60-3600),
  "tags": {"key": "value"} (optional),
  "replicas": 2 (optional, 1-10),
  "namespace": "asgard" (optional)
}
```

### Response Schema

```json
{
  "model_name": "string",
  "experiment_name": "string",
  "status": "deployed",
  "inference_url": "http://EXTERNAL_IP",
  "external_ip": "IP_ADDRESS",
  "model_version": "VERSION",
  "run_id": "MLFLOW_RUN_ID",
  "ecr_image": "ECR_IMAGE_URI",
  "endpoints": {
    "health": "http://EXTERNAL_IP/health",
    "metadata": "http://EXTERNAL_IP/metadata",
    "predict": "http://EXTERNAL_IP/predict",
    "root": "http://EXTERNAL_IP"
  },
  "deployment_time_seconds": 245.3,
  "message": "Success message"
}
```

## 🛠️ Training Script Requirements

### Must Have

Your training script **MUST** include:

1. ✅ `mlflow.start_run()` - Create an MLflow run
2. ✅ `mlflow.<framework>.log_model(model, 'model')` - Save the model
3. ✅ Model training logic

### Auto-Injected

These are **automatically added** by the API:

```python
import mlflow
mlflow.set_tracking_uri('...')  # Auto-configured
mlflow.set_experiment('...')     # From request
```

### Complete Example

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# Create dataset
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Train with MLflow
with mlflow.start_run():
    # Train
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    # Log params (optional)
    mlflow.log_params({'n_estimators': 100})

    # Log metrics (optional)
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric('accuracy', accuracy)

    # REQUIRED: Log model
    mlflow.sklearn.log_model(model, 'model')

    print(f"Accuracy: {accuracy:.4f}")
```

## 💻 Usage Examples

### Using Helper Script (Recommended)

```bash
# 1. Write your training script
cat > my_train.py << 'EOF'
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

X, y = make_classification(n_samples=1000, n_features=20)

with mlflow.start_run():
    model = RandomForestClassifier()
    model.fit(X, y)
    mlflow.sklearn.log_model(model, 'model')
EOF

# 2. Create deployment request
python ml_deployment/encode_script.py my_train.py \
  --deploy \
  --model-name my_awesome_model \
  --experiment-name production \
  --requirements scikit-learn pandas numpy \
  > request.json

# 3. Deploy
curl -X POST "http://localhost:8000/mlops/deploy" \
  -H "Content-Type: application/json" \
  -d @request.json

# 4. Extract inference URL from response
```

### Using Python

```python
import base64
import requests
import json

# Read script
with open('my_train.py', 'rb') as f:
    script_content = base64.b64encode(f.read()).decode()

# Create request
request = {
    "script_name": "my_train.py",
    "script_content": script_content,
    "experiment_name": "production",
    "model_name": "my_awesome_model",
    "requirements": ["scikit-learn==1.3.2", "pandas", "numpy"],
    "timeout": 300,
    "replicas": 2,
    "namespace": "asgard"
}

# Deploy (this will take 3-5 minutes)
print("Deploying model... (this takes 3-5 minutes)")
response = requests.post(
    "http://localhost:8000/mlops/deploy",
    json=request,
    timeout=600  # 10 minute timeout
)

result = response.json()
inference_url = result['inference_url']

print(f"✅ Deployed! Inference URL: {inference_url}")

# Make a prediction
prediction_response = requests.post(
    f"{inference_url}/predict",
    json={
        "inputs": {
            "feature1": [1.0, 2.0, 3.0],
            "feature2": [4.0, 5.0, 6.0]
        }
    }
)

print(f"Predictions: {prediction_response.json()}")
```

### Using curl with Manual Encoding

```bash
# Encode script
ENCODED_SCRIPT=$(cat my_train.py | base64 -w 0)

# Deploy
curl -X POST "http://localhost:8000/mlops/deploy" \
  -H "Content-Type: application/json" \
  -d "{
    \"script_name\": \"my_train.py\",
    \"script_content\": \"$ENCODED_SCRIPT\",
    \"experiment_name\": \"production\",
    \"model_name\": \"my_model\",
    \"requirements\": [\"scikit-learn==1.3.2\", \"pandas\", \"numpy\"],
    \"timeout\": 300,
    \"replicas\": 2,
    \"namespace\": \"asgard\"
  }"
```

## 🎯 Making Predictions

Once deployed, use the inference URL to make predictions:

```bash
# Health check
curl http://51.89.136.142/health

# Get metadata
curl http://51.89.136.142/metadata

# Make prediction
curl -X POST "http://51.89.136.142/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "feature1": [1.0, 2.0, 3.0],
      "feature2": [4.0, 5.0, 6.0],
      "feature3": [7.0, 8.0, 9.0]
    }
  }'

# Response
{
  "predictions": [0, 1, 1]
}
```

## ⚠️ Important Notes

### Timeouts

- Default training timeout: **300 seconds** (5 minutes)
- Can be increased up to **3600 seconds** (1 hour)
- API call is **synchronous** - waits for complete deployment
- Set client timeout to **600+ seconds** (10+ minutes)

### Requirements

- Script must use MLflow (injected automatically)
- Must call `mlflow.start_run()`
- Must call `mlflow.<framework>.log_model()`
- Supported frameworks: sklearn, xgboost, lightgbm, tensorflow, pytorch, etc.

### Resource Limits

- Default replicas: **2**
- Min replicas: **1**
- Max replicas: **10**
- Each replica: 512Mi-1Gi memory, 250m-1000m CPU

### Networking

- Each model gets a **unique LoadBalancer**
- External IP assigned automatically
- May take 1-2 minutes for IP allocation
- LoadBalancer costs apply (AWS)

## 🐛 Troubleshooting

### Error: "No MLflow runs found after training"

**Cause:** Your script didn't call `mlflow.start_run()`

**Fix:**

```python
with mlflow.start_run():  # ADD THIS
    model = train_model()
    mlflow.sklearn.log_model(model, 'model')
```

### Error: "No model artifact found in run"

**Cause:** You didn't log the model

**Fix:**

```python
with mlflow.start_run():
    model = train_model()
    mlflow.sklearn.log_model(model, 'model')  # ADD THIS
```

### Error: "Training script failed with exit code 1"

**Cause:** Python error in your script

**Fix:** Check the error output in the API response for details

### Error: "Failed to install requirements"

**Cause:** Invalid package name or version

**Fix:** Use exact package names: `scikit-learn==1.3.2` (not `sklearn`)

### Deployment Stuck or Slow

**Cause:** Various (image pull, resource limits, etc.)

**Check:**

```bash
# Check deployment status
kubectl get deployment -n asgard | grep model-name

# Check pod status
kubectl get pods -n asgard | grep model-name

# Check pod logs
kubectl logs -n asgard <pod-name>

# Check service
kubectl get svc -n asgard | grep model-name
```

## 📊 Monitoring

### Check Deployment Status

```bash
# List deployments
kubectl get deployments -n asgard

# List services
kubectl get svc -n asgard

# Check specific model
kubectl get all -n asgard -l app=<model-name>-inference
```

### View Logs

```bash
# Get pod name
POD=$(kubectl get pods -n asgard -l app=<model-name>-inference -o jsonpath='{.items[0].metadata.name}')

# View logs
kubectl logs -n asgard $POD

# Stream logs
kubectl logs -n asgard $POD -f
```

### Scale Deployment

```bash
# Scale up
kubectl scale deployment <model-name>-inference -n asgard --replicas=5

# Scale down
kubectl scale deployment <model-name>-inference -n asgard --replicas=1
```

## 🔗 Related Documentation

- [Example Training Scripts](./EXAMPLE_TRAINING_SCRIPT.md) - Multiple framework examples
- [MLOps API Reference](./MLOPS_API_FINAL.md) - Complete API documentation
- [Quick Reference](./MLOPS_QUICK_REFERENCE.md) - Cheat sheet
- [API Testing Guide](./API_TESTING_GUIDE.md) - Testing examples

## 📝 Summary

The `/mlops/deploy` endpoint provides:

✅ **One-click deployment** - Upload script, get inference URL  
✅ **Fully automated** - Train, build, push, deploy  
✅ **Production-ready** - LoadBalancer, health checks, scaling  
✅ **Framework agnostic** - sklearn, xgboost, tensorflow, pytorch, etc.  
✅ **No K8s knowledge needed** - Everything handled automatically

Just write your training script and deploy! 🚀
