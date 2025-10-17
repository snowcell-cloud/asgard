# MLflow on Kubernetes with AWS S3

Complete deployment guide for MLflow tracking server on Kubernetes using PostgreSQL and AWS S3.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Security](#security)

## Overview

MLflow is an open-source platform for managing the ML lifecycle. This deployment includes:

- **MLflow Tracking Server** - Experiment tracking and model registry
- **PostgreSQL** - Backend store for metadata (experiments, runs, parameters, metrics)
- **AWS S3** - Artifact store for models, plots, and files
- **Kubernetes** - Container orchestration and management

## Architecture

```
┌─────────────────────────────────────────┐
│      ML Applications / Workloads        │
└────────────────┬────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │  MLflow Tracking Server    │
    │  (Kubernetes Service)      │
    └─────┬──────────────────┬───┘
          │                  │
          ▼                  ▼
    ┌──────────┐       ┌─────────┐
    │PostgreSQL│       │ AWS S3  │
    │(Metadata)│       │(Models) │
    │   PVC    │       │ Bucket  │
    └──────────┘       └─────────┘
```

### Components

| Component     | Purpose             | Storage   |
| ------------- | ------------------- | --------- |
| MLflow Server | Tracking API & UI   | Stateless |
| PostgreSQL    | Experiment metadata | 10Gi PVC  |
| AWS S3        | Model artifacts     | S3 Bucket |

## Quick Start

### 1. Create S3 Bucket

```bash
# Set variables
export AWS_S3_BUCKET="mlflow-artifacts-prod"
export AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://${AWS_S3_BUCKET} --region ${AWS_REGION}

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket ${AWS_S3_BUCKET} \
  --versioning-configuration Status=Enabled
```

### 2. Create Kubernetes Secret

```bash
kubectl create secret generic s3-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key \
  --from-literal=AWS_REGION=us-east-1 \
  --from-literal=AWS_S3_BUCKET=mlflow-artifacts-prod \
  -n asgard
```

**Required Secret Fields:**

- `AWS_ACCESS_KEY_ID` - AWS IAM access key
- `AWS_SECRET_ACCESS_KEY` - AWS IAM secret key
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `AWS_S3_BUCKET` - S3 bucket name

**Verify the secret:**

```bash
./verify-secret.sh
```

### 3. Deploy MLflow

```bash
cd mlflow
./deploy.sh
```

### 4. Access MLflow UI

**Option A: Port Forward (Development)**

```bash
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
```

Access at: http://localhost:5000

**Option B: Ingress (Production)**

1. Update `mlflow-ingress.yaml` with your domain
2. Apply: `kubectl apply -f mlflow-ingress.yaml`
3. Access via your configured domain

## Prerequisites

### Required

- ✅ Kubernetes cluster (1.19+)
- ✅ kubectl configured with cluster access
- ✅ `asgard` namespace created
- ✅ AWS account with S3 access
- ✅ AWS IAM credentials with S3 permissions
- ✅ StorageClass for PersistentVolumes

### Optional

- 📦 Ingress controller (nginx, traefik, etc.)
- 🔒 cert-manager for TLS certificates
- 📊 Prometheus for monitoring

## Installation

### Automated Deployment (Recommended)

```bash
./deploy.sh
```

The script will:

- ✅ Verify s3-credentials secret exists
- ✅ Deploy PostgreSQL with PVC
- ✅ Deploy MLflow tracking server
- ✅ Create services and ingress
- ✅ Wait for all pods to be ready

### Manual Deployment

#### Step 1: Deploy Storage

```bash
kubectl apply -f storage.yaml
```

Verify PVC:

```bash
kubectl get pvc -n asgard
```

#### Step 2: Deploy PostgreSQL

```bash
kubectl apply -f postgres.yaml
```

Wait for ready:

```bash
kubectl wait --for=condition=ready pod -l component=postgres -n asgard --timeout=300s
```

#### Step 3: Deploy MLflow

```bash
kubectl apply -f mlflow-deployment.yaml
kubectl apply -f mlflow-service.yaml
kubectl apply -f mlflow-ingress.yaml
```

Wait for ready:

```bash
kubectl wait --for=condition=ready pod -l component=tracking-server -n asgard --timeout=300s
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n asgard -l app=mlflow

# Expected output:
# NAME                                  READY   STATUS    RESTARTS   AGE
# mlflow-deployment-xxx                 1/1     Running   0          2m
# postgres-deployment-xxx               1/1     Running   0          3m

# Check services
kubectl get svc -n asgard -l app=mlflow

# Check logs
kubectl logs -f -n asgard -l component=tracking-server
```

## Configuration

### S3 Credentials Secret

The `s3-credentials` secret must contain exactly these 4 fields:

| Field                   | Description        | Example                 |
| ----------------------- | ------------------ | ----------------------- |
| `AWS_ACCESS_KEY_ID`     | AWS IAM access key | `AKIAIOSFODNN7EXAMPLE`  |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | `wJalrXUtnFEMI...`      |
| `AWS_REGION`            | AWS region         | `us-east-1`             |
| `AWS_S3_BUCKET`         | S3 bucket name     | `mlflow-artifacts-prod` |

**Create using template:**

See `s3-credentials-template.yaml` for a YAML template.

**Verify secret:**

```bash
./verify-secret.sh
```

### Environment Variables

MLflow deployment uses these environment variables:

```yaml
# PostgreSQL backend
MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:mlflow123@postgres-service:5432/mlflow

# AWS S3 credentials
AWS_ACCESS_KEY_ID: from s3-credentials secret
AWS_SECRET_ACCESS_KEY: from s3-credentials secret
AWS_DEFAULT_REGION: from AWS_REGION in secret

# S3 artifact root
AWS_S3_BUCKET: from s3-credentials secret
MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://$(AWS_S3_BUCKET)/mlflow-artifacts
```

### Storage Configuration

**PostgreSQL PVC:**

- Default: 10Gi
- Modify in `storage.yaml`

**S3 Bucket:**

- Configure bucket name in `s3-credentials` secret
- Recommended: Enable versioning and encryption

### Resource Limits

**MLflow Server:**

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

**PostgreSQL:**

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

Modify in respective deployment files as needed.

### Scaling

Scale MLflow horizontally:

```bash
kubectl scale deployment mlflow-deployment -n asgard --replicas=3
```

## Usage

### Python Client

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier

# Set tracking URI
mlflow.set_tracking_uri("http://mlflow-service.asgard.svc.cluster.local:5000")
# Or for local: mlflow.set_tracking_uri("http://localhost:5000")

# Create experiment
mlflow.set_experiment("my-experiment")

# Log run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)

    # Log metrics
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("f1_score", 0.93)

    # Log model
    model = RandomForestClassifier(n_estimators=100)
    mlflow.sklearn.log_model(model, "model")

    # Log artifacts
    mlflow.log_artifact("plot.png")
```

### Environment Variables for ML Workloads

```bash
export MLFLOW_TRACKING_URI=http://mlflow-service.asgard.svc.cluster.local:5000
export AWS_ACCESS_KEY_ID=your-aws-access-key
export AWS_SECRET_ACCESS_KEY=your-aws-secret-key
export AWS_REGION=us-east-1
```

### Kubernetes Job Example

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training-job
  namespace: asgard
spec:
  template:
    spec:
      containers:
        - name: training
          image: python:3.9
          env:
            - name: MLFLOW_TRACKING_URI
              value: "http://mlflow-service.asgard.svc.cluster.local:5000"
          envFrom:
            - secretRef:
                name: s3-credentials
          command: ["python", "train.py"]
      restartPolicy: Never
```

### Test Connection

```bash
python test-connection.py --tracking-uri http://localhost:5000
```

## Maintenance

### Backup PostgreSQL

```bash
# Create backup
kubectl exec -n asgard deployment/postgres-deployment -- \
  pg_dump -U mlflow mlflow > mlflow-backup-$(date +%Y%m%d).sql

# Restore backup
kubectl exec -i -n asgard deployment/postgres-deployment -- \
  psql -U mlflow mlflow < mlflow-backup-20251015.sql
```

### Backup S3 Artifacts

```bash
# Sync to backup bucket
aws s3 sync s3://mlflow-artifacts-prod s3://mlflow-artifacts-backup

# Download locally
aws s3 sync s3://mlflow-artifacts-prod ./mlflow-artifacts-backup
```

### View Logs

```bash
# MLflow logs
kubectl logs -f -n asgard -l component=tracking-server

# PostgreSQL logs
kubectl logs -f -n asgard -l component=postgres

# All MLflow components
kubectl logs -f -n asgard -l app=mlflow
```

### Monitor Resources

```bash
# Pod resource usage
kubectl top pods -n asgard -l app=mlflow

# Check events
kubectl get events -n asgard --sort-by='.lastTimestamp'
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/mlflow-deployment \
  mlflow=ghcr.io/mlflow/mlflow:v2.17.0 -n asgard

# Or edit directly
kubectl edit deployment mlflow-deployment -n asgard

# Rollout status
kubectl rollout status deployment/mlflow-deployment -n asgard

# Rollback if needed
kubectl rollout undo deployment/mlflow-deployment -n asgard
```

### Database Maintenance

```bash
# Connect to PostgreSQL
kubectl exec -it -n asgard deployment/postgres-deployment -- psql -U mlflow mlflow

# Check database size
SELECT pg_size_pretty(pg_database_size('mlflow'));

# Vacuum database
VACUUM ANALYZE;

# Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod -n asgard -l component=tracking-server

# Common issues:
# 1. Secret not found -> Create s3-credentials secret
# 2. Init containers failing -> Check PostgreSQL is running
# 3. Image pull errors -> Check image name and registry access
```

### Database Connection Errors

```bash
# Test PostgreSQL connectivity
kubectl exec -it -n asgard deployment/mlflow-deployment -- sh
nc -zv postgres-service 5432

# Check PostgreSQL logs
kubectl logs -n asgard -l component=postgres

# Verify password in deployment matches postgres secret
```

### S3 Access Errors

```bash
# Verify credentials
kubectl get secret s3-credentials -n asgard -o yaml

# Test S3 access from pod
kubectl exec -it -n asgard deployment/mlflow-deployment -- sh
# Inside pod:
aws s3 ls s3://your-bucket-name/

# Check IAM permissions
aws iam get-user
aws s3 ls s3://your-bucket-name/
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n asgard

# Check PV
kubectl get pv

# Describe PVC
kubectl describe pvc postgres-pvc -n asgard

# Common issues:
# 1. No StorageClass available
# 2. Insufficient storage
# 3. PV not binding
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n asgard

# Increase resources
kubectl edit deployment mlflow-deployment -n asgard

# Scale horizontally
kubectl scale deployment mlflow-deployment -n asgard --replicas=3
```

## Security

### Production Checklist

- [ ] Change default PostgreSQL password
- [ ] Use strong AWS IAM credentials
- [ ] Enable S3 bucket encryption
- [ ] Enable S3 bucket versioning
- [ ] Configure TLS/HTTPS for ingress
- [ ] Implement network policies
- [ ] Set up RBAC with least privilege
- [ ] Enable audit logging
- [ ] Rotate credentials regularly
- [ ] Use secrets management (Vault, AWS Secrets Manager)

### Change Default Passwords

**PostgreSQL:**

1. Update `postgres.yaml`:

```yaml
stringData:
  POSTGRES_PASSWORD: your-secure-password
```

2. Update `mlflow-deployment.yaml`:

```yaml
value: postgresql://mlflow:your-secure-password@postgres-service:5432/mlflow
```

3. Redeploy.

### Enable TLS/SSL

**Update ingress:**

```yaml
spec:
  tls:
    - hosts:
        - mlflow.yourdomain.com
      secretName: mlflow-tls-secret
```

**Create TLS secret:**

```bash
kubectl create secret tls mlflow-tls-secret \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n asgard
```

### IAM Policy for S3

Minimal IAM policy for MLflow S3 access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::mlflow-artifacts-prod",
        "arn:aws:s3:::mlflow-artifacts-prod/*"
      ]
    }
  ]
}
```

### S3 Security Best Practices

1. ✅ Enable S3 bucket encryption at rest
2. ✅ Enable S3 bucket versioning
3. ✅ Use IAM roles instead of access keys (IRSA on EKS)
4. ✅ Enable S3 access logging
5. ✅ Set up lifecycle policies
6. ✅ Use least-privilege IAM policies
7. ✅ Rotate credentials regularly
8. ✅ Enable MFA delete for production

### Network Policies

Restrict pod-to-pod communication:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mlflow-network-policy
  namespace: asgard
spec:
  podSelector:
    matchLabels:
      app: mlflow
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 5000
  egress:
    - to:
        - podSelector:
            matchLabels:
              component: postgres
      ports:
        - protocol: TCP
          port: 5432
```

## Cleanup

### Remove Deployment

```bash
# Using cleanup script
./cleanup.sh

# Or manually
kubectl delete -f mlflow-ingress.yaml
kubectl delete -f mlflow-service.yaml
kubectl delete -f mlflow-deployment.yaml
kubectl delete -f postgres.yaml
kubectl delete -f storage.yaml
kubectl delete secret s3-credentials -n asgard
```

**Note:** This will NOT delete your S3 bucket or artifacts.

### Delete S3 Bucket (if needed)

```bash
# WARNING: This deletes all artifacts!
aws s3 rb s3://mlflow-artifacts-prod --force
```

## File Structure

```
mlflow/
├── README.md                      # This file - complete documentation
├── deploy.sh                      # Automated deployment script
├── cleanup.sh                     # Cleanup script
├── verify-secret.sh               # Secret verification script
├── test-connection.py             # Connection test script
├── .gitignore                     # Git ignore rules
├── storage.yaml                   # PostgreSQL PVC
├── postgres.yaml                  # PostgreSQL deployment
├── mlflow-deployment.yaml         # MLflow server deployment
├── mlflow-service.yaml            # Kubernetes service
├── mlflow-ingress.yaml            # Ingress configuration
└── s3-credentials-template.yaml   # Secret template
```

## Support & References

### Documentation

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [MLflow Tracking](https://mlflow.org/docs/latest/tracking.html)
- [MLflow S3 Artifact Store](https://mlflow.org/docs/latest/tracking.html#amazon-s3-and-s3-compatible-storage)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

### Troubleshooting Steps

1. Check logs: `kubectl logs -n asgard -l app=mlflow`
2. Check events: `kubectl get events -n asgard`
3. Verify secret: `./verify-secret.sh`
4. Test connection: `python test-connection.py`

### Common Commands

```bash
# View all MLflow resources
kubectl get all -n asgard -l app=mlflow

# Restart MLflow
kubectl rollout restart deployment mlflow-deployment -n asgard

# View real-time logs
kubectl logs -f -n asgard -l component=tracking-server

# Port forward
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
```

---

**Version:** 1.0  
**Last Updated:** October 15, 2025  
**MLflow Version:** v2.16.2  
**Storage:** AWS S3
