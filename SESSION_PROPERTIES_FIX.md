# Final Fix - Invalid Session Properties

## Issue
After fixing the `uv run` issue, dbt now connects to Trino but fails with:
```
Session property 'iceberg.target-file-size-bytes' does not exist
```

## Root Cause
The Iceberg session properties in profiles.yml are not recognized by this Trino version. These properties:
- `iceberg.target-file-size-bytes`
- `iceberg.compression-codec`

These might be:
1. Incorrect property names for this Trino/Iceberg version
2. Not applicable in session properties
3. Should be set at table creation time, not in connection

## Fix Applied
Removed the invalid session properties from profiles.yml generation.

**Before**:
```yaml
session_properties:
  iceberg.target-file-size-bytes: "268435456"
  iceberg.compression-codec: "SNAPPY"
```

**After**:
```yaml
# No session_properties section
```

## Deploy

```bash
# Quick deploy
./quick-deploy-fix.sh

# Or manual
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
helm upgrade --install asgard ./helmchart -n asgard
```

## Test

```bash
curl -X POST http://51.89.225.64/dbt/transform \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "customer_transaction_summary",
    "sql_query": "SELECT customer_id, COUNT(*) as transactions FROM silver.t1f7840c0 GROUP BY customer_id",
    "description": "Customer transaction counts",
    "materialization": "table",
    "owner": "data-team"
  }'
```

## Expected Result
✅ Transformation should now complete successfully and create the table in `gold.customer_transaction_summary`

## Note on Iceberg Properties
If you need to set Iceberg-specific properties (like compression or file size), you should:
1. Set them at the catalog level in Trino configuration
2. Or use table properties in the dbt model config:
```sql
{{
  config(
    materialized='table',
    properties={
      'format': 'PARQUET',
      'compression': 'SNAPPY'
    }
  )
}}
```

## Status
✅ Ready to deploy - Session properties removed from profiles.yml