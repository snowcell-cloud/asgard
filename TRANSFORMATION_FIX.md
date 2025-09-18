# Fix for AWS Access Error in Transformation API

## Problem Description

The transformation API was experiencing AWS access errors because the `sql_transform_embedded.py` script (which runs inside the Spark containers) was using hardcoded fallback S3 paths instead of the paths provided by the API during the call.

### Root Cause

In `sql_transform_embedded.py`, the script had hardcoded default values:

```python
# OLD CODE - PROBLEMATIC
source_paths_json = os.getenv("SOURCE_PATHS", '["s3a://airbytedestination1/bronze/*"]')
destination_path = os.getenv("DESTINATION_PATH", "s3a://airbytedestination1/silver/default/")
```

This meant that when the environment variables weren't properly set, the script would fall back to these hardcoded paths, causing AWS access errors when trying to access the hardcoded bucket.

## Solution Implemented

### 1. Updated `sql_transform_embedded.py`

Changed the script to require environment variables and fail fast if they're missing:

```python
# NEW CODE - FIXED
sql_query = os.getenv("SQL_QUERY")
source_paths_json = os.getenv("SOURCE_PATHS")
destination_path = os.getenv("DESTINATION_PATH")

# Validate required environment variables
if not sql_query:
    print("❌ ERROR: SQL_QUERY environment variable is required")
    sys.exit(1)

if not source_paths_json:
    print("❌ ERROR: SOURCE_PATHS environment variable is required")
    print("    This should be set by the transformation API")
    sys.exit(1)

if not destination_path:
    print("❌ ERROR: DESTINATION_PATH environment variable is required")
    print("    This should be set by the transformation API")
    sys.exit(1)
```

### 2. Updated ConfigMap (`k8s/04-configmap.yaml`)

Applied the same fix to the ConfigMap version of the script to ensure consistency.

### 3. Cleaned Up Unused ConfigMap Reference

Removed unused ConfigMap volume mount from the SparkApplication spec since the script is embedded in the Docker image.

## How It Works Now

1. **API Request**: User calls `/transform` endpoint with optional `source_path` parameter
2. **Service Processing**: The transformation service processes the request and:
   - Uses the provided `source_path` if specified
   - Converts S3 URLs to S3A format for Spark compatibility
   - Generates a unique destination path
3. **SparkApplication Creation**: The service creates a SparkApplication with environment variables:
   - `SQL_QUERY`: The SQL to execute
   - `SOURCE_PATHS`: JSON array of source paths
   - `DESTINATION_PATH`: The destination path
   - `WRITE_MODE`: Write mode (overwrite/append)
4. **Spark Execution**: The Spark container runs `/opt/spark/sql_transform.py` which:
   - Validates all required environment variables are present
   - Fails fast with clear error messages if any are missing
   - Uses only the API-provided paths (no hardcoded fallbacks)

## Files Modified

1. **`sql_transform_embedded.py`**: Added environment variable validation
2. **`k8s/04-configmap.yaml`**: Updated ConfigMap script with same validation
3. **`app/data_transformation/client.py`**: Removed unused ConfigMap volume mount

## Testing

Created comprehensive tests in `test_transformation_paths.py` that verify:

- ✅ SparkApplication specs correctly set environment variables
- ✅ API-provided paths are properly passed through the entire flow
- ✅ No hardcoded fallback paths are used

## Benefits

1. **No More AWS Access Errors**: The script will only use paths that the API has access to
2. **Clear Error Messages**: If environment variables are missing, the job fails with clear error messages
3. **Proper Path Handling**: API-provided source paths are correctly used instead of defaults
4. **Better Debugging**: Failed jobs will now show exactly why they failed (missing env vars)

## Example Usage

```json
POST /transform
{
    "sql": "SELECT customer_id, SUM(amount) as total FROM source_data GROUP BY customer_id",
    "source_path": "s3://my-bucket/data/bronze/customers/"
}
```

This will now correctly:

- Read from `s3a://my-bucket/data/bronze/customers/`
- Write to `s3a://my-bucket/silver/{generated-run-id}/`
- Use the same AWS credentials and access permissions as the API
