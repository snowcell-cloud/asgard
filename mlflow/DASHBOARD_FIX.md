# MLflow Dashboard Port-Forward Fix

**Date**: October 28, 2025  
**Issue**: MLflow dashboard not opening properly when port forwarding

---

## 🔍 Root Cause Analysis

### Issues Identified:

1. **Worker Timeout (Primary Issue)**

   - Gunicorn workers were timing out after 120 seconds
   - Causing frequent worker crashes and restarts
   - Error: `[CRITICAL] WORKER TIMEOUT (pid:XX)`

2. **Insufficient Workers**

   - Only 2 workers configured
   - Not enough to handle concurrent requests during dashboard loading

3. **Incorrect Static Prefix**
   - `--static-prefix=/static` flag was breaking the root path routing
   - Causing 404 errors on the main dashboard URL

---

## ✅ Solutions Applied

### 1. Increased Worker Timeout

```yaml
--gunicorn-opts="--timeout 300 --workers 4 ..."
```

- Changed from 120s → **300s** (5 minutes)
- Prevents worker timeouts during heavy operations

### 2. Increased Worker Count

```yaml
--workers 4
```

- Changed from 2 → **4 workers**
- Better concurrent request handling

### 3. Removed Static Prefix

```yaml
# Removed: --static-prefix=/static
```

- Allows proper routing to root path `/`
- MLflow handles static files internally

### 4. Added Keep-Alive

```yaml
--keep-alive 5
```

- Maintains connections between requests
- Reduces connection overhead

---

## 🧪 Verification Steps

### Test Script Created

`/mlflow/test-mlflow-connection.sh` - Automated testing script that:

1. ✅ Checks pod status
2. ✅ Scans logs for errors
3. ✅ Verifies service connectivity
4. ✅ Tests health endpoint
5. ✅ Cleans up old port-forwards
6. ✅ Starts new port-forward

### Manual Verification

```bash
# 1. Check pod is running
kubectl get pods -n asgard -l app=mlflow
# Result: Running with 4 healthy workers

# 2. Check logs
kubectl logs <mlflow-pod> -n asgard --tail=30
# Result: No worker timeouts, health checks passing

# 3. Port forward
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# 4. Test endpoints
curl http://localhost:5000/health
# Result: OK

curl http://localhost:5000/
# Result: <title>MLflow</title> ✅
```

---

## 📊 Before vs After

| Metric               | Before    | After    | Improvement |
| -------------------- | --------- | -------- | ----------- |
| Worker Timeout       | 120s      | 300s     | +150%       |
| Worker Count         | 2         | 4        | +100%       |
| Worker Crashes       | Frequent  | None     | ✅          |
| Dashboard Load       | 404 Error | ✅ Works | Fixed       |
| Connection Stability | Timeouts  | Stable   | ✅          |

---

## 🚀 How to Access MLflow Dashboard

### Option 1: Port Forward (Local Development)

```bash
# Start port forward
kubectl port-forward -n asgard svc/mlflow-service 5000:5000

# Access in browser
http://localhost:5000
```

### Option 2: Use Test Script

```bash
cd mlflow
./test-mlflow-connection.sh
# Follow prompts, then open http://localhost:5000
```

### Option 3: Ingress (Production)

```bash
# Check ingress
kubectl get ingress -n asgard mlflow-ingress
# Access via configured domain
```

---

## 📝 Configuration Changes

### File: `mlflow/mlflow-deployment.yaml`

**Changed Lines:**

```yaml
# Before:
--gunicorn-opts="--timeout 120 --workers 2 --worker-class sync"

# After:
--gunicorn-opts="--timeout 300 --workers 4 --worker-class sync --keep-alive 5"
```

**Full Command:**

```yaml
mlflow server \
--host=0.0.0.0 \
--port=5000 \
--backend-store-uri=${MLFLOW_BACKEND_STORE_URI} \
--default-artifact-root=${MLFLOW_DEFAULT_ARTIFACT_ROOT} \
--serve-artifacts \
--gunicorn-opts="--timeout 300 --workers 4 --worker-class sync --keep-alive 5"
```

---

## 🔧 Troubleshooting

### If Dashboard Still Not Loading:

1. **Check Pod Status**

   ```bash
   kubectl get pods -n asgard -l app=mlflow
   # Should show: Running
   ```

2. **Check Logs for Errors**

   ```bash
   kubectl logs -n asgard <mlflow-pod> --tail=50
   # Look for: WORKER TIMEOUT, ERROR, CRITICAL
   ```

3. **Verify Port Forward**

   ```bash
   curl http://localhost:5000/health
   # Should return: OK
   ```

4. **Check Service**

   ```bash
   kubectl get svc -n asgard mlflow-service
   # Should show: ClusterIP with port 5000
   ```

5. **Restart Deployment**
   ```bash
   kubectl rollout restart deployment/mlflow-deployment -n asgard
   kubectl rollout status deployment/mlflow-deployment -n asgard
   ```

### Common Errors:

**Error**: `WORKER TIMEOUT`  
**Solution**: Already fixed with timeout increase to 300s

**Error**: `404 Not Found` on root path  
**Solution**: Already fixed by removing `--static-prefix`

**Error**: `Connection refused` on localhost:5000  
**Solution**: Ensure port-forward is running, restart if needed

---

## ✅ Status

- **Issue**: ✅ RESOLVED
- **MLflow Dashboard**: ✅ ACCESSIBLE
- **Port Forwarding**: ✅ WORKING
- **Worker Stability**: ✅ STABLE

**Access Now**:

```bash
kubectl port-forward -n asgard svc/mlflow-service 5000:5000
# Then open: http://localhost:5000
```

---

**Fixed By**: Copilot  
**Date**: October 28, 2025  
**Status**: ✅ Production Ready
