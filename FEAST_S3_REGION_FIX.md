# Feast API Fix - S3 Region Configuration

## Issue

Feast API was failing to create feature views with error:

```
AWS Error UNKNOWN (HTTP status 301) during HeadObject operation:
No response body. Looks like the configured region is '' while the
bucket is located in 'eu-north-1'.
```

## Root Cause

The `app/feast/service.py` was creating `feature_store.yaml` without the `region` parameter in the `offline_store` configuration.

## Fix Applied

Updated `app/feast/service.py` line 115 to include region:

```python
offline_store:
    type: file
    region: {self.aws_region}  # <-- ADDED THIS LINE
    # Reads directly from S3 Parquet files created by Iceberg
```

## Files Modified

- ✅ `app/feast/service.py` - Added region to offline_store config
- ✅ `test_feast_api_real_table.py` - Updated to skip model training (no date column)

## Deployment Steps

1. **Build new image:**

   ```bash
   docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest .
   ```

2. **Push to ECR:**

   ```bash
   aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com
   docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
   ```

3. **Restart deployment:**

   ```bash
   kubectl rollout restart deployment asgard-app -n asgard
   kubectl wait --for=condition=ready pod -l app=asgard-app -n asgard --timeout=120s
   ```

4. **Run tests:**
   ```bash
   python3 test_feast_api_real_table.py
   ```

## Expected Results After Fix

### ✅ Working Endpoints

- GET `/feast/status` - Feature store status
- GET `/feast/features` - List feature views
- GET `/feast/models` - List models
- POST `/feast/features` - Create feature view (FIXED)
- POST `/feast/features/service` - Create feature service (FIXED)

### ⚠️ Skipped Tests

- POST `/feast/models` - Requires timestamp column (table has none)
- POST `/feast/predictions/batch` - Requires trained model

## Test Table Info

- **Table:** `iceberg.gold.efxgs5oersyezxnzydx4vsyou04jna6ti5`
- **Columns:** order_id, product_id, produced_units, operator_name
- **Entity:** order_id
- **Note:** No timestamp/date column available for time-based operations

## Next Steps

1. Wait for Docker build to complete
2. Push image to ECR
3. Restart deployment
4. Run comprehensive tests
5. Verify feature view creation succeeds

---

**Status:** In Progress  
**Date:** October 13, 2025  
**Image:** 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest
