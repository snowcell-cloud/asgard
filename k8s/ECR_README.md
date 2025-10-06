# ECR Secret Auto-Refresh

Automatically refreshes ECR secrets every 12 hours using IAM roles.

## Files

- `ecr-secret-refresh-cronjob.yaml` - CronJob that runs every 12 hours
- `ecr-secret-rbac.yaml` - Required RBAC permissions

## Check Status

```bash
kubectl get cronjob ecr-secret-refresh -n asgard
kubectl get jobs -n asgard -l job-name=ecr-secret-refresh
```

## Manual Test

```bash
kubectl create job --from=cronjob/ecr-secret-refresh ecr-secret-test -n asgard
```
