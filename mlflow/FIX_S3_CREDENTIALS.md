# Fixing S3 Credentials for MLOps Training

## Current Issue

When training scripts try to save model artifacts to MLflow, they fail with:

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Impact:**

- ✅ Training completes successfully
- ✅ Metrics and parameters are logged
- ❌ Model artifacts are NOT saved to S3

## Solution

### Option 1: Add AWS Credentials as Kubernetes Secret (Recommended)

1. **Create the secret:**

```bash
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID='your-access-key-id' \
  --from-literal=AWS_SECRET_ACCESS_KEY='your-secret-access-key' \
  --from-literal=AWS_DEFAULT_REGION='us-east-1' \
  -n asgard
```

2. **Update the Asgard deployment to use the secret:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asgard-service
  namespace: asgard
spec:
  template:
    spec:
      containers:
        - name: asgard
          env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: AWS_ACCESS_KEY_ID
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: AWS_SECRET_ACCESS_KEY
            - name: AWS_DEFAULT_REGION
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: AWS_DEFAULT_REGION
```

3. **Restart the deployment:**

```bash
kubectl rollout restart deployment/asgard-service -n asgard
kubectl rollout status deployment/asgard-service -n asgard
```

### Option 2: Use IAM Role for Service Account (IRSA) - Best for AWS EKS

1. **Create IAM policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-mlflow-bucket/*",
        "arn:aws:s3:::your-mlflow-bucket"
      ]
    }
  ]
}
```

2. **Create IAM role and associate with service account:**

```bash
eksctl create iamserviceaccount \
  --name asgard-service-account \
  --namespace asgard \
  --cluster your-cluster-name \
  --attach-policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/MLflowS3Access \
  --approve
```

3. **Update deployment to use service account:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: asgard-service
  namespace: asgard
spec:
  template:
    spec:
      serviceAccountName: asgard-service-account
```

### Option 3: Configure in Training Script

Add credentials directly in environment variables when uploading script:

```python
response = requests.post("http://localhost:8000/mlops/training/upload", json={
    "script_name": "churn_model.py",
    "script_content": script_b64,
    "experiment_name": "customer_churn",
    "model_name": "churn_predictor",
    "environment_vars": {
        "AWS_ACCESS_KEY_ID": "your-key-id",
        "AWS_SECRET_ACCESS_KEY": "your-secret-key",
        "AWS_DEFAULT_REGION": "us-east-1"
    }
})
```

⚠️ **Not recommended for production** - credentials in plain text

## Verification

After adding credentials, test with:

```bash
python mlflow/test_training_with_feast.py
```

You should see:

```
✓ Model logged to MLflow
✓ Model artifact path: model/model.pkl
```

Instead of:

```
⚠️  Model artifact logging skipped (S3 credentials needed)
```

## Alternative: Use Local Storage (Development Only)

For testing without S3:

1. **Update MLflow to use local storage:**

```bash
# In MLflow deployment
MLFLOW_ARTIFACT_ROOT=/tmp/mlartifacts
```

2. **Mount persistent volume for artifacts:**

```yaml
volumes:
  - name: mlflow-artifacts
    persistentVolumeClaim:
      claimName: mlflow-artifacts-pvc
```

⚠️ **Not recommended for production** - artifacts not durable

## Current Workaround

The system gracefully handles missing S3 credentials:

- Training completes successfully ✅
- Metrics and parameters are logged ✅
- Model artifacts are skipped (with warning) ⚠️
- Run ID is captured for later registration ✅

You can manually register models later using the run ID:

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.register_model(
    model_uri=f"runs://{run_id}/model",
    name="churn_predictor"
)
```

## Next Steps

1. ✅ Choose credential method (Option 1 recommended)
2. ⬜ Add AWS credentials to Kubernetes
3. ⬜ Restart Asgard deployment
4. ⬜ Re-run test to verify artifacts are saved
5. ⬜ Confirm model registration works

---

**Status:** Training works, only artifact storage needs credentials ✅
