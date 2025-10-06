# Quick Reference: Trino Connection Fixes

## What Changed

### Configuration Updates

| Component          | Before                               | After                    |
| ------------------ | ------------------------------------ | ------------------------ |
| Trino Host         | `trino-coordinator.data-platform...` | `trino.data-platform...` |
| Trino User         | `trino`                              | `dbt`                    |
| HTTP Scheme        | Missing                              | `http`                   |
| Threads            | 1                                    | 4                        |
| Session Properties | Missing                              | Added Iceberg configs    |

### Files Modified

1. ✅ `app/dbt_transformations/service.py` - Trino connection defaults
2. ✅ `helmchart/values.yaml` - Environment variables
3. ✅ Created `test-trino-connection.sh` - Diagnostic tool
4. ✅ Created `TRINO_CONNECTION_FIX.md` - Deployment guide

## Minimal Deployment Steps

```bash
# 1. Build and push
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest

# 2. Deploy
helm upgrade --install asgard ./helmchart -n asgard

# 3. Test
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{"name":"test_transform","sql_query":"SELECT 1 as test","description":"test","materialization":"table","owner":"admin"}'
```

## Root Cause

The dbt-trino adapter was failing to connect because:

1. Wrong service name (trino-coordinator vs trino)
2. Wrong user (trino vs dbt)
3. Missing http_scheme parameter
4. Missing Iceberg session properties

## Expected Result

After deployment, the transformation API will successfully:

- Connect to Trino at `trino.data-platform.svc.cluster.local:8080`
- Execute SQL queries using dbt user
- Create tables in the gold schema
- Return success response instead of connection errors
