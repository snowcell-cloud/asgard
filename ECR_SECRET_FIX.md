# ECR Secret Name Mismatch Fix

## Problem

The deployment was failing with `ImagePullBackOff` error due to ECR authentication issues:

- Error: `Unable to retrieve some image pull secrets (ecr-secret)`
- Root cause: Secret name mismatch

## Root Cause

- **CronJob was creating**: `ecr-credentials`
- **Deployment was expecting**: `ecr-secret`

## Files Changed

1. `k8s/ecr-credentials.yaml` - Updated to use `ecr-secret` instead of `ecr-credentials`
2. `k8s/fix-ecr-secret.sh` - New script to quickly fix the issue

## Quick Fix

Run the fix script:

```bash
cd /home/hac/downloads/code/asgard-dev
chmod +x k8s/fix-ecr-secret.sh
./k8s/fix-ecr-secret.sh
```

## Manual Fix Steps

If you prefer to fix manually:

1. **Delete old incorrectly named secret:**

   ```bash
   kubectl delete secret ecr-credentials -n asgard --ignore-not-found=true
   ```

2. **Create correctly named secret:**

   ```bash
   aws ecr get-login-password --region eu-north-1 | \
   kubectl create secret docker-registry ecr-secret \
     --docker-server=637423187518.dkr.ecr.eu-north-1.amazonaws.com \
     --docker-username=AWS \
     --docker-password="$(cat -)" \
     -n asgard
   ```

3. **Reapply the updated CronJob:**

   ```bash
   kubectl apply -f k8s/ecr-credentials.yaml
   ```

4. **Force pod recreation:**
   ```bash
   kubectl delete pods -n asgard -l app=asgard-app
   # Or if that doesn't work:
   kubectl get pods -n asgard
   kubectl delete pod <pod-name> -n asgard
   ```

## Verification

1. **Check secret exists:**

   ```bash
   kubectl get secret ecr-secret -n asgard
   ```

2. **Check secret content:**

   ```bash
   kubectl get secret ecr-secret -n asgard -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq
   ```

3. **Check pod status:**

   ```bash
   kubectl get pods -n asgard
   kubectl describe pod <pod-name> -n asgard
   ```

4. **Check CronJob:**
   ```bash
   kubectl get cronjob ecr-secret-refresh -n asgard
   ```

## Future Prevention

The CronJob now refreshes credentials every 11 hours (ECR tokens expire after 12 hours) using the correct secret name `ecr-secret`.

To manually trigger the CronJob:

```bash
kubectl create job --from=cronjob/ecr-secret-refresh ecr-secret-refresh-manual -n asgard
```

## Expected Timeline

- Secret creation: Immediate
- Pod restart: 1-2 minutes
- Image pull: 2-5 minutes depending on image size
- Pod ready: 3-7 minutes total

## Monitoring Commands

```bash
# Watch pod status
kubectl get pods -n asgard -w

# Check events
kubectl get events -n asgard --sort-by='.lastTimestamp'

# Check deployment status
kubectl get deployment -n asgard

# Check CronJob history
kubectl get jobs -n asgard -l app=ecr-credentials
```
