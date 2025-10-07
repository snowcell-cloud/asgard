# DBT Transformations API - Complete Resolution Guide

## Issue Timeline & Fixes

### Issue #1: Permission Denied ✅ FIXED

**Error**: `[Errno 13] Permission denied: '/home/hac'`  
**Fix**: Use writable temp directory `/tmp/dbt_projects`

### Issue #2: Module Not Found ✅ FIXED

**Error**: `dbt run failed: failed after 3 attempts`  
**Fix**: Run dbt with `uv run dbt` to access installed packages

### Issue #3: Invalid Session Properties ✅ FIXED

**Error**: `Session property 'iceberg.target-file-size-bytes' does not exist`  
**Fix**: Removed unsupported session properties from profiles.yml

### Issue #4: Schema Not Found ⚠️ ACTION REQUIRED

**Error**: `Schema 'silver' does not exist`  
**Fix**: Create missing schemas in Iceberg catalog

## Current Status

✅ **Working**: DBT connects to Trino successfully  
✅ **Working**: DBT can execute transformations  
✅ **Working**: Gold schema auto-creation  
⚠️ **Needs Action**: Create `silver` schema for source tables

## Quick Fix - Create Missing Schemas

### Option A: Automated Script

```bash
./create-schemas.sh
```

### Option B: Manual Creation

```bash
# Create silver schema
kubectl run -n asgard create-silver --image=curlimages/curl --rm -i --restart=Never -- \
  curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
    -H 'X-Trino-User: dbt' \
    -H 'X-Trino-Catalog: iceberg' \
    -d 'CREATE SCHEMA IF NOT EXISTS iceberg.silver'

# Create gold schema (done automatically by the app, but you can create it manually too)
kubectl run -n asgard create-gold --image=curlimages/curl --rm -i --restart=Never -- \
  curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
    -H 'X-Trino-User: dbt' \
    -H 'X-Trino-Catalog: iceberg' \
    -d 'CREATE SCHEMA IF NOT EXISTS iceberg.gold'
```

## Full Deployment Process

### Step 1: Create Schemas

```bash
chmod +x create-schemas.sh
./create-schemas.sh
```

### Step 2: Build and Deploy

```bash
# Build image
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .

# Authenticate to ECR
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com

# Push image
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest

# Deploy with Helm
helm upgrade --install asgard ./helmchart -n asgard --wait

# Verify deployment
kubectl get pods -n asgard
kubectl logs -n asgard -l app=asgard-app --tail=50
```

### Step 3: Test the API

#### Test 1: Simple Transformation (No Dependencies)

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "simple_test",
    "sql_query": "SELECT 1 as test_col, CURRENT_TIMESTAMP as created_at",
    "description": "Simple test transformation",
    "materialization": "table",
    "owner": "admin"
  }'
```

**Expected Response**:

```json
{
  "id": "uuid-here",
  "name": "simple_test",
  "status": "completed",
  "gold_table_name": "gold.simple_test",
  "row_count": 1,
  "created_at": "2025-10-06T...",
  "updated_at": "2025-10-06T..."
}
```

#### Test 2: Transformation from Silver to Gold

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "customer_transaction_summary",
    "sql_query": "SELECT customer_id, COUNT(*) as transaction_count FROM iceberg.silver.t1f7840c0 GROUP BY customer_id",
    "description": "Customer transaction summary from silver to gold",
    "materialization": "table",
    "owner": "data-team"
  }'
```

**Note**: Use fully qualified table names (`iceberg.silver.table_name`) to avoid ambiguity.

## Verification Checklist

- [ ] Schemas created (silver and gold)
- [ ] Docker image built and pushed
- [ ] Helm deployment successful
- [ ] Pod is running and healthy
- [ ] Simple test transformation works
- [ ] Silver-to-gold transformation works

## Troubleshooting

### If schemas still don't exist:

```bash
# Check schemas via Python
POD=$(kubectl get pods -n asgard -l app=asgard-app -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n asgard $POD -- uv run python3 << 'EOF'
from trino.dbapi import connect
conn = connect(
    host='trino.data-platform.svc.cluster.local',
    port=8080,
    user='dbt',
    catalog='iceberg',
    schema='default',
    http_scheme='http'
)
cursor = conn.cursor()
cursor.execute('SHOW SCHEMAS')
for schema in cursor.fetchall():
    print(schema[0])
EOF
```

### If table doesn't exist in silver:

```bash
# List tables in silver schema
kubectl exec -n asgard $POD -- uv run python3 << 'EOF'
from trino.dbapi import connect
conn = connect(
    host='trino.data-platform.svc.cluster.local',
    port=8080,
    user='dbt',
    catalog='iceberg',
    schema='silver',
    http_scheme='http'
)
cursor = conn.cursor()
cursor.execute('SHOW TABLES')
print('Tables in silver schema:')
for table in cursor.fetchall():
    print(f'  - {table[0]}')
EOF
```

### If transformation fails:

```bash
# Check pod logs
kubectl logs -n asgard -l app=asgard-app --tail=100

# Check dbt logs inside pod
kubectl exec -n asgard $POD -- cat /tmp/dbt_projects/logs/dbt.log
```

## Architecture Summary

```
API Request → FastAPI → DBTTransformationService
                           ↓
                    Create schemas (if needed)
                           ↓
                    Generate dbt model
                           ↓
                    Execute: uv run dbt run
                           ↓
                    Trino (iceberg catalog)
                           ↓
                    silver.* → gold.*
                           ↓
                    Return transformation results
```

## Key Configuration

- **Trino Host**: `trino.data-platform.svc.cluster.local:8080`
- **Catalog**: `iceberg`
- **Schemas**: `silver` (source), `gold` (destination)
- **User**: `dbt`
- **DBT Project**: `/tmp/dbt_projects` (auto-created)
- **Python Environment**: `uv` managed

## Files Modified

1. `Dockerfile` - Added temp directory, environment variables
2. `app/dbt_transformations/service.py` - All fixes applied
3. `helmchart/values.yaml` - Production configuration
4. `create-schemas.sh` - Schema creation automation

## Next Steps

1. ✅ Run `./create-schemas.sh` to create required schemas
2. ✅ Deploy the application
3. ✅ Test with simple transformation first
4. ✅ Then test with actual silver → gold transformations
5. ✅ Monitor logs and verify gold tables are created

## Success Criteria

✅ API returns 200 status  
✅ Transformation status is "completed"  
✅ Gold table exists in Trino  
✅ Gold table contains expected data  
✅ No errors in application logs

## Status: 🎯 READY TO DEPLOY (After Creating Schemas)

All code fixes are complete. Just need to create the schemas and deploy!
