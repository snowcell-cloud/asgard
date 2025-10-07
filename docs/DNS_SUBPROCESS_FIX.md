# DNS Resolution Fix for DBT Subprocess

## Issue

DNS resolution fails when dbt runs as a subprocess:

```
Failed to resolve 'trino.data-platform.svc.cluster.local' ([Errno -2] Name or service not known)
```

## Root Cause

The subprocess.run() calls were NOT passing environment variables to the child process. While Python in the main process could resolve DNS correctly, the dbt subprocess couldn't access the same environment.

## Fix Applied

### 1. Pass Environment Variables to Subprocess

Updated `_execute_dbt_run` method to explicitly pass environment:

```python
# Before
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

# After
env = os.environ.copy()
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
```

### 2. Added DNS Debugging

Before running dbt, test DNS resolution:

```python
import socket
resolved_ip = socket.gethostbyname(self.trino_host)
print(f"{self.trino_host} resolves to {resolved_ip}")
```

### 3. Added profiles.yml Logging

Log the generated Trino connection details to verify configuration.

## Deploy the Fix

```bash
# Build and push
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest

# Deploy
helm upgrade --install asgard ./helmchart -n asgard --wait

# Verify
kubectl get pods -n asgard
kubectl logs -n asgard -l app=asgard-app --tail=100 -f
```

## Test the API

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "test_dns_fix",
    "sql_query": "SELECT 1 as test_col",
    "description": "Test DNS resolution fix",
    "materialization": "table",
    "owner": "admin"
  }'
```

## Expected Behavior

You should see in the logs:

```
🔍 DNS Test before dbt run:
   trino.data-platform.svc.cluster.local resolves to 10.3.79.43
📝 Generated profiles.yml:
   Host: trino.data-platform.svc.cluster.local
   Port: 8080
   ...
```

Then dbt should successfully connect and execute the transformation.

## Verification

After deployment, check logs:

```bash
POD=$(kubectl get pods -n asgard -l app=asgard-app -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n asgard $POD --tail=200
```

Look for:

- ✅ DNS resolution success message
- ✅ profiles.yml generation log
- ✅ DBT debug output showing connection success
- ✅ Transformation completion

## Why This Happened

Python's `subprocess.run()` by default does NOT inherit the parent process's environment variables unless explicitly told to do so via the `env` parameter. This meant:

- Main Python process: ✅ Has environment, DNS works
- DBT subprocess: ❌ Missing environment, DNS fails

## Status

✅ Fix applied - Environment variables now properly passed to dbt subprocess
