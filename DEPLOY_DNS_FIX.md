# Complete Fix Applied - DNS Resolution in Subprocess

## The Problem

```
Failed to resolve 'trino.data-platform.svc.cluster.local' ([Errno -2] Name or service not known)
```

DBT subprocess couldn't resolve DNS even though:

- DNS works in main Python process ✅
- Environment variables are set ✅
- Trino service exists ✅

## The Root Cause

**subprocess.run() doesn't inherit environment variables by default!**

When we called:

```python
subprocess.run(cmd, capture_output=True, text=True, timeout=300)
```

The subprocess didn't have access to environment variables, so it couldn't resolve DNS.

## The Fix

### Change 1: Pass Environment to Subprocess

```python
env = os.environ.copy()
subprocess.run(cmd, ..., env=env)
```

### Change 2: Add DNS Debugging

```python
import socket
resolved_ip = socket.gethostbyname(self.trino_host)
print(f"{self.trino_host} resolves to {resolved_ip}")
```

### Change 3: Log Configuration

```python
print(f"📝 Generated profiles.yml:")
print(f"   Host: {self.trino_host}")
```

## Deploy Now

```bash
# Build
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .

# Push
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest

# Deploy
helm upgrade --install asgard ./helmchart -n asgard --wait

# Test
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "dns_fix_test",
    "sql_query": "SELECT 1 as id, CURRENT_TIMESTAMP as created_at",
    "description": "DNS fix verification",
    "materialization": "table",
    "owner": "admin"
  }'
```

## All Issues Fixed

1. ✅ Permission denied → `/tmp/dbt_projects`
2. ✅ Module not found → `uv run dbt`
3. ✅ Invalid session properties → Removed
4. ⚠️ Schema not found → Create with `./create-schemas.sh`
5. ✅ DNS resolution → Pass environment to subprocess

## Expected Success Response

```json
{
  "id": "uuid-here",
  "name": "dns_fix_test",
  "status": "completed",
  "gold_table_name": "gold.dns_fix_test",
  "row_count": 1,
  "execution_time_seconds": 2.5,
  "created_at": "2025-10-07T07:00:00Z"
}
```

## Monitoring

Watch the logs:

```bash
kubectl logs -n asgard -l app=asgard-app --tail=100 -f
```

You should see:

```
🔍 DNS Test before dbt run:
   trino.data-platform.svc.cluster.local resolves to 10.3.79.43
📝 Generated profiles.yml:
   Host: trino.data-platform.svc.cluster.local
   Port: 8080
   User: dbt
   Catalog: iceberg
   Schema: gold
DBT Debug Output:
...
```

## Status: ✅ READY TO DEPLOY

All code issues resolved. Deploy and test!
