# Asgard Platform - Onboarding & Setup Guide

**Complete Setup Instructions**  
**Last Updated:** November 11, 2025  
**Version:** 1.0  


---

## 📋 Table of Contents

1. [What is Asgard?](#what-is-asgard)
2. [Prerequisites](#prerequisites)
3. [Quick Start  ](#quick-start-5-minutes)
4. [Complete Installation](#complete-installation)
5. [Initial Configuration](#initial-configuration)
6. [Verify Installation](#verify-installation)
7. [First Steps](#first-steps)
8. [Next Steps](#next-steps)

---

## What is Asgard?

**Asgard** is a unified data platform that orchestrates the complete data lifecycle from raw data ingestion to ML model deployment through a **single REST API**.

### One-Sentence Summary

> "FastAPI-powered data lakehouse that orchestrates Airbyte, Spark, DBT, Feast, and MLflow for end-to-end ML workflows on Kubernetes."

### The Complete Pipeline

```
External DBs → Airbyte → Spark → DBT → Feast → MLOps
    ↓           ↓         ↓       ↓      ↓       ↓
 Sources     Bronze    Silver   Gold  Features Models
```

### What You'll Get

✅ **Data Ingestion** - Connect to PostgreSQL, MySQL, APIs (Airbyte)  
✅ **Data Processing** - Clean and transform data (Spark on Kubernetes)  
✅ **Business Analytics** - SQL-based transformations (DBT + Trino)  
✅ **Feature Engineering** - ML-ready features (Feast + Iceberg)  
✅ **ML Training** - Train models with MLflow tracking  
✅ **Model Serving** - Deploy models for real-time inference  
✅ **Data Lakehouse** - Apache Iceberg on S3 with Nessie catalog

---

## Prerequisites

### Required Tools

| Tool           | Version | Purpose                 | Installation                                               |
| -------------- | ------- | ----------------------- | ---------------------------------------------------------- |
| **Kubernetes** | 1.27+   | Container orchestration | [Install kubectl](https://kubernetes.io/docs/tasks/tools/) |
| **Helm**       | 3.0+    | Package manager         | [Install Helm](https://helm.sh/docs/intro/install/)        |
| **Docker**     | 20.10+  | Container runtime       | [Install Docker](https://docs.docker.com/get-docker/)      |
| **Python**     | 3.11+   | Client scripts          | [Install Python](https://www.python.org/downloads/)        |
| **curl**       | Latest  | API testing             | Pre-installed on most systems                             


### Cloud Resources (Optional)

| Resource               | Purpose             | Provider                           |
| ---------------------- | ------------------- | ---------------------------------- |
| **S3 Bucket**          | Artifact storage    | AWS, MinIO, or compatible          |
| **PostgreSQL**         | Metadata storage    | AWS RDS, Cloud SQL, or self-hosted |
| **Kubernetes Cluster** | Platform deployment | EKS, GKE, AKS, or minikube         |

### Access Requirements

- Kubernetes cluster admin access (for installation)
- Namespace creation permissions
- Port-forwarding capabilities (for local access)
- AWS credentials (if using S3)

---

## Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
# Clone Asgard repository
git clone https://github.com/your-org/asgard-dev.git
cd asgard-dev
```

### Step 2: Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace asgard

# Deploy Asgard using Helm
helm install asgard ./helmchart \
  --namespace asgard \
  --set image.repository=your-registry/asgard \
  --set image.tag=latest
```

### Step 3: Port Forward API

```bash
# Forward Asgard API to local machine
kubectl port-forward -n asgard svc/asgard-app 8000:80
```

### Step 4: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Access Swagger UI
open http://localhost:8000/docs
```

**Expected Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "airbyte": "connected",
    "spark": "ready",
    "dbt": "ready",
    "feast": "connected",
    "mlflow": "connected"
  }
}
```

✅ **You're ready!** Continue to [First Steps](#first-steps)

---

## Complete Installation

### 1. Deploy Infrastructure Components

#### Deploy MLflow

```bash
# Deploy MLflow tracking server
kubectl apply -f mlflow/postgres.yaml
kubectl apply -f mlflow/storage.yaml
kubectl apply -f mlflow/mlflow-deployment.yaml
kubectl apply -f mlflow/mlflow-service.yaml
kubectl apply -f mlflow/mlflow-ingress.yaml

# Wait for MLflow to be ready
kubectl wait -n asgard --for=condition=ready pod -l app=mlflow --timeout=300s
```

#### Deploy Airbyte (Optional)

```bash
# Add Airbyte Helm repo
helm repo add airbyte https://airbytehq.github.io/helm-charts
helm repo update

# Install Airbyte
helm install airbyte airbyte/airbyte \
  --namespace asgard \
  --set global.edition=community
```

#### Deploy Spark Operator

```bash
# Add Spark Operator Helm repo
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator
helm repo update

# Install Spark Operator
helm install spark-operator spark-operator/spark-operator \
  --namespace asgard \
  --set sparkJobNamespace=asgard
```

### 2. Configure AWS Credentials (If Using S3)

```bash
# Create AWS credentials secret
kubectl create secret generic aws-credentials \
  --namespace asgard \
  --from-literal=AWS_ACCESS_KEY_ID=your-access-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key \
  --from-literal=AWS_DEFAULT_REGION=us-east-1

# Apply ECR credentials (if using ECR)
kubectl apply -f k8s/ecr-credentials.yaml
```

### 3. Deploy Asgard Application

```bash
# Deploy using Helm
helm install asgard ./helmchart \
  --namespace asgard \
  --set image.repository=your-registry/asgard \
  --set image.tag=latest \
  --set env.AWS_S3_BUCKET=your-bucket-name \
  --set env.MLFLOW_TRACKING_URI=http://mlflow-service:5000

# Verify deployment
kubectl get pods -n asgard
```

### 4. Set Up Port Forwarding

```bash
# Forward Asgard API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# Forward MLflow UI
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# Forward Airbyte UI (if deployed)
kubectl port-forward -n asgard svc/airbyte-webapp-svc 8001:80 &
```

---

## Initial Configuration

### 1. Configure Environment Variables

Create a `.env` file or set environment variables:

```bash
# API Configuration
export ASGARD_API_URL=http://localhost:8000

# AWS Configuration
export AWS_S3_BUCKET=your-bucket-name
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# MLflow Configuration
export MLFLOW_TRACKING_URI=http://localhost:5000

# Airbyte Configuration (optional)
export AIRBYTE_API_URL=http://localhost:8001/api/v1
```

### 2. Initialize Feast Repository

```bash
# The Feast repository is auto-configured in the Asgard deployment
# Verify it's working
curl http://localhost:8000/feast/status
```

### 3. Configure Iceberg Catalog

```bash
# Nessie catalog is pre-configured
# Verify connectivity
curl http://localhost:8000/data-products/status
```

---

## Verify Installation

### 1. Check All Services

```bash
# Check Asgard API
curl http://localhost:8000/health | jq

# Check MLflow
curl http://localhost:5000/health | jq

# Check Feast status
curl http://localhost:8000/feast/status | jq

# Check Airbyte (if deployed)
curl http://localhost:8001/api/v1/health | jq
```

### 2. Check Kubernetes Resources

```bash
# Check all pods are running
kubectl get pods -n asgard

# Expected output:
# NAME                          READY   STATUS    RESTARTS   AGE
# asgard-app-xxxxxxxxxx-xxxxx   1/1     Running   0          5m
# mlflow-xxxxxxxxxx-xxxxx       1/1     Running   0          10m
# postgres-xxxxxxxxxx-xxxxx     1/1     Running   0          10m
# spark-operator-xxxxx          1/1     Running   0          10m

# Check services
kubectl get svc -n asgard

# Check ingresses
kubectl get ingress -n asgard
```

### 3. Access Web UIs

| Service             | URL                          | Purpose                                |
| ------------------- | ---------------------------- | -------------------------------------- |
| **Asgard API Docs** | http://localhost:8000/docs   | Interactive API documentation          |
| **MLflow UI**       | http://localhost:5000        | Experiment tracking and model registry |
| **Airbyte UI**      | http://localhost:8001        | Data connector configuration           |
| **Health Check**    | http://localhost:8000/health | Platform status                        |

---
 
   