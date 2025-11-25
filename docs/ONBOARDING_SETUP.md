# Asgard Platform - Onboarding & Setup Guide

**Complete Setup Instructions**  
**Last Updated:** November 25, 2025  
**Version:** 1.1
---

**Key Capabilities:**

- Data ingestion via Airbyte
- Data processing with Spark on Kubernetes
- SQL transformations using DBT + Trino
- Feature engineering with Feast + Iceberg
- ML training and deployment with MLflow
- Unified REST API built with FastAPI

---

## Prerequisites

### Required

| Tool        | Version | Purpose         |
| ----------- | ------- | --------------- |
| **kubectl** | 1.27+   | Kubernetes CLI  |
| **Helm**    | 3.0+    | Package manager |
| **Python**  | 3.11+   | Development     |
| **curl**    | Any     | API testing     |

### Cluster Requirements

- Kubernetes cluster with admin access
- Namespace creation permissions
- S3-compatible storage (AWS S3 or MinIO)
- PostgreSQL database (for MLflow metadata)

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/asgard.git
cd asgard
```

### 2. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 3. Deploy Asgard

Using the Helm chart with default values:

```bash
helm install asgard ./helmchart --namespace asgard
```

### 4. Access the API

```bash
# Port forward the service
kubectl port-forward -n asgard svc/asgard-app 8000:80

# Access Swagger UI
open http://localhost:8000/docs
```

✅ **Installation complete!** Your Asgard platform is now running.

---

## Complete Installation

### Step 1: Deploy Kubernetes Resources

#### Create Namespace and RBAC

```bash
# Create the asgard namespace
kubectl apply -f k8s/namespace.yaml

# Create Spark RBAC permissions
kubectl apply -f k8s/spark-rbac.yaml
```

#### Deploy MLflow (Optional)

If you need MLflow tracking:

```bash
# Deploy in order
kubectl apply -f mlflow/postgres.yaml
kubectl apply -f mlflow/storage.yaml
kubectl apply -f mlflow/mlflow-deployment.yaml
kubectl apply -f mlflow/mlflow-service.yaml
kubectl apply -f mlflow/mlflow-ingress.yaml

# Verify MLflow is running
kubectl get pods -n asgard -l app=mlflow
```

### Step 2: Configure Secrets

#### AWS/S3 Credentials

```bash
# Create S3 credentials secret
kubectl create secret generic s3-credentials \
  --namespace asgard \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key \
  --from-literal=AWS_REGION=us-east-1
```

#### ECR Authentication (if using AWS ECR)

```bash
# Create ECR secret for pulling images
kubectl apply -f k8s/ecr-auto-refresh-cronjob.yaml
```

### Step 3: Deploy Asgard Application

#### Using Helm Chart

Edit `helmchart/values.yaml` or override values:

```bash
helm install asgard ./helmchart \
  --namespace asgard \
  --set image.repository=637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard \
  --set image.tag=latest \
  --set env.SPARK_IMAGE=637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom:latest
```

#### Using Custom Values File

Create a custom `my-values.yaml`:

```yaml
image:
  repository: your-registry/asgard
  tag: latest

env:
  AIRBYTE_BASE_URL: "http://airbyte-server:8001/api/public/v1"
  TRINO_HOST: "trino.data-platform.svc.cluster.local"
  NESSIE_URI: "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
```

<!--
Deploy with custom values:

```bash
helm install asgard ./helmchart -f my-values.yaml --namespace asgard
```

### Step 4: Set Up External Dependencies

#### Deploy Airbyte (Optional)

```bash
helm repo add airbyte https://airbytehq.github.io/helm-charts
helm repo update
helm install airbyte airbyte/airbyte --namespace airbyte --create-namespace
```

#### Deploy Spark Operator

```bash
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator
helm install spark-operator spark-operator/spark-operator \
  --namespace asgard \
  --set sparkJobNamespace=asgard
``` -->

---

## Configuration

### Environment Variables Reference

The application is configured via `helmchart/values.yaml`. Key environment variables:

```yaml
env:
  # Core Settings
  ENVIRONMENT: "production"
  PIPELINE_NAMESPACE: "asgard"
  SPARK_NAMESPACE: "asgard"

  # Airbyte Integration
  AIRBYTE_BASE_URL: "http://airbyte-server:8001/api/public/v1"

  # Spark Configuration
  SPARK_IMAGE: "your-registry/spark-custom:latest"
  SPARK_SERVICE_ACCOUNT: "spark-sa"
  S3_SECRET_NAME: "s3-credentials"

  # Trino/Iceberg
  TRINO_HOST: "trino.data-platform.svc.cluster.local"
  TRINO_PORT: "8080"
  TRINO_CATALOG: "iceberg"

  # Nessie Catalog
  NESSIE_URI: "http://nessie:19120/api/v1"
  NESSIE_REF: "main"

  # Feast Feature Store
  FEAST_REPO_PATH: "/tmp/feast_repo"

  # Storage Paths
  MODEL_STORAGE_PATH: "/tmp/models"
  DBT_PROJECT_DIR: "/tmp/dbt_projects"
```

### Local Development Setup

For local development, copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
ENVIRONMENT=development
AIRBYTE_BASE_URL=http://localhost:8001/api/public/v1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
SPARK_IMAGE=your-registry/spark-custom:latest
```

### Service Accounts

The deployment creates a service account `asgard-app` for the API and `spark-sa` for Spark jobs (configured in `k8s/spark-rbac.yaml`)

---

## Verify Installation

### Check Deployment Status

```bash
# Check all pods are running
kubectl get pods -n asgard

# Expected output:
# NAME                          READY   STATUS    RESTARTS   AGE
# asgard-app-xxxxxxxxxx-xxxxx   1/1     Running   0          5m
```

### Check Services

```bash
# List all services
kubectl get svc -n asgard

# Expected services:
# NAME          TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)
# asgard-app    LoadBalancer   10.100.x.x      <pending>     80:xxxxx/TCP
```

### Check Ingress (if enabled)

```bash
kubectl get ingress -n asgard
```

### Test API Health

```bash
# Port forward first
kubectl port-forward -n asgard svc/asgard-app 8000:80

# Check health endpoint
curl http://localhost:8000/health

# Access interactive API docs
open http://localhost:8000/docs
```

### Access MLflow (if deployed)

```bash
# Port forward MLflow
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# Access MLflow UI
open http://localhost:5000
```

---

## Next Steps

### 1. Explore the API

Open the interactive API documentation:

```bash
open http://localhost:8000/docs
```

Key endpoints to try:

- `GET /health` - Check platform status
- `GET /airbyte/connections` - List data connections
- `GET /feast/feature-views` - List feature views

### 2. Run Your First Pipeline

See the [Platform Documentation](./PLATFORM_DOCUMENTATION_AND_VIDEO.md) for complete examples.

### 3. Learn the Architecture

Review [Complete Architecture](./COMPLETE_ARCHITECTURE.md) for system diagrams and data flow.

### 4. Configure Integrations

- **Airbyte**: Set up data source connections
- **Spark**: Configure processing jobs
- **DBT**: Create SQL transformations
- **Feast**: Define feature views
- **MLflow**: Track experiments

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod logs
kubectl logs -n asgard deployment/asgard-app

# Describe pod for events
kubectl describe pod -n asgard -l app=asgard-app
```

### Image Pull Errors

If using ECR, ensure the secret is created:

```bash
kubectl get secret -n asgard ecr-secret
```

### Service Connection Issues

Check that dependent services are accessible:

```bash
# Test Trino connection
kubectl run -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl http://trino.data-platform.svc.cluster.local:8080

# Test Nessie connection
kubectl run -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl http://nessie.data-platform.svc.cluster.local:19120/api/v1
```

### Check Helm Release

```bash
# List Helm releases
helm list -n asgard

# Check release status
helm status asgard -n asgard

# View release values
helm get values asgard -n asgard
```

---

## Upgrade

To upgrade an existing installation:

```bash
# Pull latest changes
git pull origin main

# Upgrade Helm release
helm upgrade asgard ./helmchart -n asgard
```

To upgrade with new values:

```bash
helm upgrade asgard ./helmchart -n asgard -f my-values.yaml
```

---

## Uninstall

To completely remove Asgard:

```bash
# Uninstall Helm release
helm uninstall asgard -n asgard

# Delete namespace (WARNING: This deletes all data)
kubectl delete namespace asgard
```

---

## CI/CD Workflows

Asgard includes two automated GitHub Actions workflows for building and deploying the platform.

### 1. Main Application Deployment (`deploy.yml`)

**Workflow:** `.github/workflows/deploy.yml`

**Trigger:** Automatically runs on push to `dev` branch

**What it does:**

1. Builds the Asgard FastAPI application Docker image
2. Pushes image to AWS ECR (`637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest`)
3. Deploys to Kubernetes cluster using Helm
4. Upgrades the `asgard-app` release in the `asgard` namespace

**Required GitHub Secrets:**

- `AWS_ACCESS_KEY_ID` - AWS credentials for ECR access
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `KUBECONFIG` - Kubernetes cluster configuration (base64 encoded or plain text)

**Usage:**

```bash
# Push to dev branch to trigger deployment
git push origin dev
```

### 2. Spark Image Builder (`build-spark-image.yml`)

**Workflow:** `.github/workflows/build-spark-image.yml`

**Trigger:**

- Push to `dev` branch when these files change:
  - `spark.Dockerfile`
  - `.github/workflows/build-spark-image.yml`
  - `sql_transform_embedded.py`
- Manual trigger via `workflow_dispatch`

**What it does:**

1. Builds custom Spark image with S3 support from `spark.Dockerfile`
2. Runs comprehensive tests:
   - Spark installation verification
   - Python and PySpark import tests
   - S3A dependencies check
   - AWS CLI verification
3. Pushes image to ECR (`637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom`)
4. Updates deployment files with new image tag
5. Runs security scan on the image

**Required GitHub Secrets:**

- `AWS_ACCESS_KEY_ID` - AWS credentials for ECR access
- `AWS_SECRET_ACCESS_KEY` - AWS secret key

**Usage:**

```bash
# Automatic trigger on file changes
git add spark.Dockerfile
git commit -m "Update Spark configuration"
git push origin dev

# Or trigger manually from GitHub Actions UI
# Go to Actions → Build and Push Spark S3 Image to ECR → Run workflow
```

**Manual Workflow Trigger:**
You can also trigger the Spark image build manually without pushing code:

```bash
# Using GitHub CLI
gh workflow run build-spark-image.yml
```

### Setting Up Workflows

To use these workflows in your fork:

1. **Configure AWS Credentials:**

   ```bash
   # In your GitHub repository settings → Secrets and variables → Actions
   # Add the following secrets:
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   KUBECONFIG=your-kubeconfig-content
   ```

2. **Update ECR Registry:**
   If using a different AWS account, update the ECR registry in both workflow files:

   ```yaml
   env:
     ECR_REGISTRY: your-account-id.dkr.ecr.your-region.amazonaws.com
   ```

3. **Test Workflows:**

   ```bash
   # Push to dev branch
   git checkout dev
   git push origin dev

   # Monitor workflow execution
   gh run list --workflow=deploy.yml
   gh run list --workflow=build-spark-image.yml
   ```

### Workflow Benefits

- ✅ **Automated Builds** - No manual Docker builds required
- ✅ **Continuous Deployment** - Push code and it deploys automatically
- ✅ **Image Testing** - Spark image is tested before deployment
- ✅ **Security Scanning** - Automatic vulnerability scanning
- ✅ **Version Tracking** - Images tagged with Git commit SHA
- ✅ **Zero Downtime** - Helm upgrade ensures smooth deployments

---

## Additional Resources

- **[Complete Documentation](./PLATFORM_DOCUMENTATION_AND_VIDEO.md)** - Full platform guide with examples
- **[Architecture Diagrams](./COMPLETE_ARCHITECTURE.md)** - Visual system architecture
- **[API Reference](http://localhost:8000/docs)** - Interactive API documentation
- **[GitHub Repository](https://github.com/snowcell-cloud/asgard-dev)** - Source code and issues

---

**Questions or Issues?**  
Open an issue on GitHub or contact the platform team.
