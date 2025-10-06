# Schema Not Found Error - Fix Guide

## Current Error

```
Schema 'silver' does not exist
```

## Root Cause

The SQL query references `silver.t1f7840c0` but the `silver` schema doesn't exist in your Iceberg catalog.

## Solutions

### Option 1: Create the Missing Schemas (Recommended)

Run these commands in Trino to create the required schemas:

```sql
-- Connect to Trino (via CLI or query interface)
CREATE SCHEMA IF NOT EXISTS iceberg.silver;
CREATE SCHEMA IF NOT EXISTS iceberg.gold;
```

**Using kubectl:**

```bash
# Method 1: Via curl to Trino REST API
kubectl run -n asgard create-schemas --image=curlimages/curl --rm -i --restart=Never -- sh -c "
curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
  -H 'X-Trino-User: dbt' \
  -H 'X-Trino-Catalog: iceberg' \
  -H 'X-Trino-Schema: default' \
  -d 'CREATE SCHEMA IF NOT EXISTS iceberg.silver'
"

kubectl run -n asgard create-schemas --image=curlimages/curl --rm -i --restart=Never -- sh -c "
curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
  -H 'X-Trino-User: dbt' \
  -H 'X-Trino-Catalog: iceberg' \
  -H 'X-Trino-Schema: default' \
  -d 'CREATE SCHEMA IF NOT EXISTS iceberg.gold'
"
```

**Using Trino CLI (if available):**

```bash
# Connect to Trino pod
kubectl exec -it -n data-platform trino-59c4d5df45-tqpzk -- trino

# In Trino CLI:
CREATE SCHEMA IF NOT EXISTS iceberg.silver;
CREATE SCHEMA IF NOT EXISTS iceberg.gold;
```

### Option 2: Use Fully Qualified Table Names

Update your SQL query to use the full catalog.schema.table format:

```sql
-- Instead of:
SELECT customer_id, COUNT(*) FROM silver.t1f7840c0 GROUP BY customer_id

-- Use:
SELECT customer_id, COUNT(*) FROM iceberg.silver.t1f7840c0 GROUP BY customer_id
```

### Option 3: Verify and Use Existing Schemas

Check what schemas actually exist:

```bash
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
schemas = cursor.fetchall()

print('Available schemas in iceberg catalog:')
for schema in schemas:
    print(f'  - {schema[0]}')

cursor.close()
conn.close()
EOF
```

## What Changed in Code

### Added Auto-Schema Creation

The service now attempts to create the `gold` schema automatically before running transformations:

```python
async def _ensure_schemas_exist(self):
    """Ensure required schemas exist in Trino/Iceberg."""
    conn = connect(...)
    cursor = conn.cursor()
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.gold_schema}")
```

### Enhanced Error Messages

Better error messages when schemas don't exist, guiding users on how to fix the issue.

## Deployment

After creating the schemas, deploy the updated code:

```bash
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
helm upgrade --install asgard ./helmchart -n asgard
```

## Testing

### Test 1: Simple Query (No Schema Reference)

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "simple_test",
    "sql_query": "SELECT 1 as test_col, 2 as another_col",
    "description": "Simple test transformation",
    "materialization": "table",
    "owner": "test"
  }'
```

### Test 2: With Fully Qualified Table Name

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "customer_txn_summary",
    "sql_query": "SELECT customer_id, COUNT(*) as transactions FROM iceberg.silver.t1f7840c0 GROUP BY customer_id",
    "description": "Customer transactions",
    "materialization": "table",
    "owner": "data-team"
  }'
```

## Verification Commands

### Check if schemas exist:

```bash
# Via Trino REST API
curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
  -H 'X-Trino-User: dbt' \
  -H 'X-Trino-Catalog: iceberg' \
  -H 'X-Trino-Schema: default' \
  -d 'SHOW SCHEMAS'
```

### Check if table exists:

```bash
curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
  -H 'X-Trino-User: dbt' \
  -H 'X-Trino-Catalog: iceberg' \
  -H 'X-Trino-Schema: silver' \
  -d 'SHOW TABLES'
```

## Expected Result

After creating schemas and deploying:
✅ The `gold` schema is automatically created
✅ Transformations that reference existing schemas work
✅ Better error messages guide you if schemas are missing

## Status

⚠️ **ACTION REQUIRED**: Create `silver` schema in Iceberg catalog before running transformations that reference it.

## Quick Fix

```bash
# Create the silver schema
kubectl run -n asgard create-silver-schema --image=curlimages/curl --rm -i --restart=Never -- \
  curl -X POST 'http://trino.data-platform.svc.cluster.local:8080/v1/statement' \
    -H 'X-Trino-User: dbt' \
    -H 'X-Trino-Catalog: iceberg' \
    -d 'CREATE SCHEMA IF NOT EXISTS iceberg.silver'

# Then redeploy and test
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
helm upgrade --install asgard ./helmchart -n asgard
```
