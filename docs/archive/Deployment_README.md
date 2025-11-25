# Kubernetes Manifests

This folder contains essential Kubernetes manifests for the Asgard Data Platform that are not managed by Helm.

## 📂 Essential Files

### RBAC & Service Accounts

#### **spark-rbac.yaml** - Spark Service Account and RBAC
**Purpose**: Service account and permissions for Spark jobs to run in Kubernetes

**What it does**:
- Creates `spark-sa` ServiceAccount
- Grants permissions to create/manage pods, services, configmaps
- Required for Spark Transformation API to submit jobs

**Apply**:
```bash
kubectl apply -f k8s/spark-rbac.yaml
```

**Verify**:
```bash
kubectl get serviceaccount spark-sa -n asgard
kubectl get role spark-driver-role -n asgard
```

---

#### **ecr-credentials.yaml** - ECR Secret Management
**Purpose**: Manage AWS ECR credentials for pulling Docker images

**What it does**:
- Creates ServiceAccount for ECR secret management
- Grants permissions to manage secrets
- Optional: CronJob to auto-refresh ECR tokens

**Apply**:
```bash
kubectl apply -f k8s/ecr-credentials.yaml
```

---

### Namespace Configuration

#### **namespace.yaml** - Asgard Namespace
**Purpose**: Create the main Asgard namespace

**Apply**:
```bash
kubectl apply -f k8s/namespace.yaml
```

---

## 🚀 Deployment Methods

### Method 1: Helm Deployment (Recommended)

The primary deployment method uses Helm:

```bash
# Deploy with Helm
helm upgrade --install asgard ./helmchart \
  -n asgard \
  --create-namespace \
  --wait

# Or use the ops script
./script/asgard-ops.sh full-deploy
```

**What Helm manages**:
- Deployment
- Service
- Ingress
- ServiceAccount
- HPA (Horizontal Pod Autoscaler)
- Environment variables
- Secrets references

See **[helmchart/](../helmchart/)** for Helm chart details.

---

### Method 2: Direct kubectl (Alternative)

For development or testing, you can use kubectl directly:

```bash
# Apply RBAC
kubectl apply -f k8s/spark-rbac.yaml
kubectl apply -f k8s/ecr-credentials.yaml

# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy using Helm
helm upgrade --install asgard ./helmchart -n asgard
```

---

## 📋 Required Setup Steps

### 1. Create Namespace
```bash
kubectl create namespace asgard
# Or
kubectl apply -f k8s/namespace.yaml
```

### 2. Create S3 Credentials Secret
```bash
kubectl create secret generic s3-credentials \
  -n asgard \
  --from-literal=AWS_ACCESS_KEY_ID=your-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret
```

### 3. Apply RBAC for Spark
```bash
kubectl apply -f k8s/spark-rbac.yaml
```

### 4. (Optional) Setup ECR Auto-Refresh
```bash
kubectl apply -f k8s/ecr-credentials.yaml
```

### 5. Deploy Application
```bash
# Using ops script
./script/asgard-ops.sh full-deploy

# Or using Helm directly
helm upgrade --install asgard ./helmchart -n asgard
```

---

## 🔧 Configuration Files

### Secrets Required

| Secret Name | Type | Purpose | Keys |
|------------|------|---------|------|
| `s3-credentials` | Opaque | S3 access | AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY |
| `ecr-credentials` | docker-registry | ECR access | (auto-generated) |

### ServiceAccounts

| Name | Namespace | Purpose |
|------|-----------|---------|
| `spark-sa` | asgard | Spark job execution |
| `ecr-secret-updater` | asgard | ECR secret refresh |
| `asgard` | asgard | Main application (Helm) |

---

## 📁 Archive Folder

The **[archive/](./archive/)** folder contains historical and deprecated Kubernetes manifests:

- Old deployment configurations
- ConfigMap-based deployments
- Redundant RBAC files
- Development/test manifests

**See [archive/README.md](./archive/README.md)** for details.

---

## 🎯 Quick Reference

### Apply All Required Manifests
```bash
# Apply all essential manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/spark-rbac.yaml
kubectl apply -f k8s/ecr-credentials.yaml

# Create secrets
kubectl create secret generic s3-credentials \
  -n asgard \
  --from-literal=AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
```

### Deploy Application
```bash
# Recommended: Use ops script
./script/asgard-ops.sh setup
./script/asgard-ops.sh full-deploy

# Or Helm directly
helm upgrade --install asgard ./helmchart -n asgard
```

### Check Status
```bash
# Check all resources
kubectl get all -n asgard

# Check specific resources
kubectl get pods -n asgard
kubectl get svc -n asgard
kubectl get ingress -n asgard

# Check RBAC
kubectl get serviceaccount -n asgard
kubectl get role,rolebinding -n asgard
```

### View Logs
```bash
# Application logs
kubectl logs -n asgard -l app=asgard --tail=100 -f

# Spark job logs (example)
kubectl logs -n asgard sql-exec-<run-id>-driver

# Use ops script
./script/asgard-ops.sh logs
```

---

## 🔍 Troubleshooting

### Spark Jobs Not Starting

**Check**:
```bash
# Verify service account
kubectl get serviceaccount spark-sa -n asgard

# Verify RBAC
kubectl get role spark-driver-role -n asgard
kubectl get rolebinding spark-driver-rolebinding -n asgard

# Re-apply RBAC
kubectl apply -f k8s/spark-rbac.yaml
```

### ECR Image Pull Errors

**Check**:
```bash
# Verify ECR secret
kubectl get secret ecr-credentials -n asgard

# Manually refresh ECR secret
kubectl delete secret ecr-credentials -n asgard
./script/asgard-ops.sh setup  # This recreates the secret
```

### S3 Access Errors

**Check**:
```bash
# Verify S3 credentials
kubectl get secret s3-credentials -n asgard

# Update credentials
kubectl create secret generic s3-credentials \
  -n asgard \
  --from-literal=AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 📚 Additional Resources

- **[Main Documentation](../docs/DOCUMENTATION.md)** - Complete platform documentation
- **[Script Operations](../script/README.md)** - Deployment scripts
- **[Helm Chart](../helmchart/README.md)** - Helm chart details
- **[Archive](./archive/README.md)** - Historical manifests

---

## 🛠️ Development Notes

### Adding New Manifests

1. Create manifest in `k8s/` folder
2. Document in this README
3. Update deployment scripts if needed
4. Test thoroughly

### Helm vs Direct Manifests

**Use Helm for**:
- Main application deployment
- Service and ingress
- Environment-specific config
- Scaling and updates

**Use Direct Manifests for**:
- RBAC and service accounts
- One-time setup resources
- Shared infrastructure
- Cross-namespace resources

---

**Last Updated**: October 7, 2024  
**Maintained By**: Asgard Data Platform Team
