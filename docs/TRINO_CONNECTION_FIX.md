# Trino Connection Fix - Deployment Guide

## Issue Identified

API returning error:

```
"dbt run failed: INFO:trino.client:failed after 3 attempts"
```

## Root Causes Fixed

### 1. ✅ Incorrect Trino Host

**Problem**: Configuration had `trino-coordinator.data-platform.svc.cluster.local`  
**Solution**: Updated to `trino.data-platform.svc.cluster.local` (matching your profiles.yml)

### 2. ✅ Incorrect Trino User

**Problem**: Using `trino` as user  
**Solution**: Changed to `dbt` (matching your profiles.yml)

### 3. ✅ Missing Connection Parameters

**Problem**: profiles.yml was missing critical parameters  
**Solution**: Added `http_scheme: http` and Iceberg session properties

## Files Updated

### 1. `app/dbt_transformations/service.py`

- Updated default Trino host to `trino.data-platform.svc.cluster.local`
- Changed default user to `dbt`
- Enhanced profiles.yml generation with proper connection parameters:
  ```yaml
  http_scheme: http
  threads: 4
  session_properties:
    iceberg.target-file-size-bytes: "268435456"
    iceberg.compression-codec: "SNAPPY"
  ```

### 2. `helmchart/values.yaml`

- Updated `TRINO_HOST` to `trino.data-platform.svc.cluster.local`
- Updated `TRINO_USER` to `dbt`

## Deployment Steps

### Step 1: Verify Trino Service

First, check that the Trino service exists and is accessible:

```bash
# From your local machine
kubectl get svc -n data-platform | grep trino

# Expected output should show a service named "trino"
```

### Step 2: Test Connection from Pod (Optional but Recommended)

```bash
# Get the current asgard pod name
POD_NAME=$(kubectl get pods -n asgard -l app=asgard -o jsonpath='{.items[0].metadata.name}')

# Copy the test script to the pod
kubectl cp test-trino-connection.sh asgard/$POD_NAME:/tmp/test-trino-connection.sh

# Run the diagnostic script
kubectl exec -n asgard $POD_NAME -- bash /tmp/test-trino-connection.sh
```

### Step 3: Build and Push New Image

```bash
# Build with timestamp tag
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP} .

# Authenticate to ECR (if needed)
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com

# Push the image
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP}

# Also tag as latest
docker tag 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP} \
  637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
```

### Step 4: Update Helm Deployment

```bash
# Option A: Use latest tag (if you tagged as latest)
helm upgrade --install asgard ./helmchart -n asgard

# Option B: Use specific timestamp tag
helm upgrade --install asgard ./helmchart -n asgard \
  --set image.tag=${TIMESTAMP}
```

### Step 5: Verify Deployment

```bash
# Check pod status
kubectl get pods -n asgard

# Watch logs for any errors
kubectl logs -n asgard -l app=asgard --tail=100 -f

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=asgard -n asgard --timeout=120s
```

### Step 6: Test the API

```bash
curl -X 'POST' \
  'http://51.89.225.64/dbt/transform' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "test_customer_transactions",
    "sql_query": "SELECT customer_id, COUNT(*) as transaction_count FROM silver.t1f7840c0 GROUP BY customer_id",
    "description": "Customer transaction counts",
    "materialization": "table",
    "owner": "data-team"
  }'
```

## Troubleshooting

### If you still get connection errors:

1. **Check Trino service name**:

   ```bash
   kubectl get svc -n data-platform
   ```

   If the service name is different, update `TRINO_HOST` in values.yaml

2. **Check network policies**:

   ```bash
   kubectl get networkpolicies -n data-platform
   kubectl get networkpolicies -n asgard
   ```

   Ensure traffic is allowed from asgard namespace to data-platform

3. **Test direct connection**:

   ```bash
   kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
     curl -v http://trino.data-platform.svc.cluster.local:8080/v1/info
   ```

4. **Check Trino logs**:

   ```bash
   kubectl logs -n data-platform -l app=trino --tail=50
   ```

5. **Verify Trino is accepting connections**:
   ```bash
   kubectl exec -n asgard -it $(kubectl get pod -n asgard -l app=asgard -o name | head -1) -- \
     curl -s http://trino.data-platform.svc.cluster.local:8080/v1/info
   ```

## Expected Behavior After Fix

✅ **Before**: `failed after 3 attempts`  
✅ **After**: Transformation executes successfully and creates table in gold schema

The API should now:

1. Accept the transformation request
2. Connect to Trino successfully
3. Execute the SQL query
4. Create/update the table in the gold schema
5. Return transformation metadata with status "completed"

## Configuration Summary

**Trino Connection**:

- Host: `trino.data-platform.svc.cluster.local`
- Port: `8080`
- User: `dbt`
- Catalog: `iceberg`
- Schema: `gold`
- HTTP Scheme: `http`
- Method: `none` (no authentication)

**Environment Variables Set**:

```yaml
TRINO_HOST: "trino.data-platform.svc.cluster.local"
TRINO_PORT: "8080"
TRINO_USER: "dbt"
TRINO_CATALOG: "iceberg"
GOLD_SCHEMA: "gold"
SILVER_SCHEMA: "silver"
```

## Quick Deployment Command

If you're confident in the changes, run this one-liner:

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S) && \
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP} . && \
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP} && \
docker tag 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TIMESTAMP} \
  637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest && \
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest && \
helm upgrade --install asgard ./helmchart -n asgard && \
kubectl rollout status deployment/asgard -n asgard
```

🎯 **Status**: Ready for deployment with Trino connection fixes!
