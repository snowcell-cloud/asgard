# ECR Secret Auto-Refresh Setup

## Overview

Automatically refreshes AWS ECR credentials every 11 hours (before the 12-hour expiration) using a Kubernetes CronJob.

## Components

### 1. CronJob: `ecr-secret-auto-refresh`

- **Schedule**: `0 */11 * * *` (every 11 hours)
- **Purpose**: Refreshes ECR authentication token before expiration
- **Location**: `k8s/ecr-auto-refresh-cronjob.yaml`

### 2. ConfigMap: `ecr-refresh-script`

Contains the bash script that:

- Installs kubectl in the container
- Authenticates with AWS ECR
- Creates/updates the `ecr-secret` with fresh credentials
- Adds timestamp annotation for tracking

### 3. Secret: `ecr-secret`

- **Type**: `kubernetes.io/dockerconfigjson`
- **Labels**:
  - `app: ecr-credentials`
  - `managed-by: cronjob`
- **Annotations**:
  - `last-updated`: Timestamp of last refresh

### 4. RBAC Resources

- **ServiceAccount**: `ecr-secret-updater`
- **Role**: Permissions to get/create/update secrets
- **RoleBinding**: Links ServiceAccount to Role

## Setup Instructions

1. **Create AWS credentials secret** (if not exists):

```bash
kubectl create secret generic aws-credentials \
  --from-literal=AWS_ACCESS_KEY_ID=your-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-secret \
  -n asgard
```

2. **Deploy the CronJob**:

```bash
kubectl apply -f k8s/ecr-auto-refresh-cronjob.yaml
```

3. **Verify CronJob**:

```bash
kubectl get cronjob -n asgard
```

## Testing

### Manual Trigger

Test the refresh immediately without waiting for the schedule:

```bash
kubectl create job --from=cronjob/ecr-secret-auto-refresh ecr-test-$(date +%s) -n asgard
```

### Check Job Status

```bash
kubectl get jobs -n asgard | grep ecr-test
kubectl logs job/ecr-test-<timestamp> -n asgard
```

### Verify Secret Update

```bash
# Check timestamp annotation
kubectl get secret ecr-secret -n asgard -o jsonpath='{.metadata.annotations.last-updated}'

# Check full secret details
kubectl get secret ecr-secret -n asgard -o yaml
```

### Test Pod Deployment

Deploy a test pod to verify the secret works:

```bash
kubectl apply -f k8s/test-ecr-secret.yaml
kubectl get pods -n asgard | grep ecr-secret-test
kubectl logs <pod-name> -n asgard
```

## Monitoring

### Check CronJob Schedule

```bash
kubectl get cronjob ecr-secret-auto-refresh -n asgard
```

### View Job History

```bash
kubectl get jobs -n asgard | grep ecr
```

### Check Secret Age

```bash
kubectl get secret ecr-secret -n asgard -o jsonpath='{.metadata.annotations.last-updated}'
```

## How It Works

1. **CronJob triggers** every 11 hours
2. **Job pod starts** with AWS CLI image
3. **Script runs**:
   - Installs kubectl
   - Gets ECR password using AWS CLI
   - Creates Docker config JSON
   - Updates Kubernetes secret with new credentials
   - Adds `last-updated` timestamp
4. **Pods use secret** via `imagePullSecrets` to pull ECR images

## ECR Configuration

- **Registry**: `637423187518.dkr.ecr.eu-north-1.amazonaws.com`
- **Region**: `eu-north-1`
- **Token Expiration**: 12 hours
- **Refresh Schedule**: 11 hours (1-hour safety margin)

## Troubleshooting

### Check if secret is being used

```bash
kubectl describe secret ecr-secret -n asgard
kubectl get pods -n asgard -o jsonpath='{.items[*].spec.imagePullSecrets[*].name}' | tr ' ' '\n' | sort -u
```

### View recent job logs

```bash
kubectl get jobs -n asgard --sort-by=.metadata.creationTimestamp | grep ecr | tail -1
kubectl logs job/<job-name> -n asgard
```

### ImagePullBackOff issues

1. Check if image exists in ECR
2. Verify secret is mounted: `kubectl describe pod <pod-name> -n asgard`
3. Check secret timestamp is recent
4. Manually trigger a refresh job

## Files

- `ecr-auto-refresh-cronjob.yaml` - Main CronJob and ConfigMap
- `test-ecr-secret.yaml` - Test deployment to verify functionality
- `refresh-ecr-secret.sh` - Standalone refresh script (manual use)

## Success Indicators

✅ CronJob shows `LAST SCHEDULE` updating every 11 hours  
✅ Secret annotation `last-updated` timestamp is recent  
✅ Test pods can pull ECR images successfully  
✅ Job logs show "✅ Refresh completed!"
