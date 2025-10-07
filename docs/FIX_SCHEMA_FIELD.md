# Schema Field Name Fix - transformation_id

## 🐛 Error Found

```
Transformation creation failed: 500: Transformation execution failed:
1 validation error for DBTTransformationResponse
transformation_id
  Field required [type=missing, input_value={'id': '652f8846-7d59-451...time_seconds': 8.077229}, input_type=dict]
```

## 🔍 Root Cause

The `DBTTransformationResponse` Pydantic schema expects a field named `transformation_id`, but the service code was creating a dictionary with the field named `id`.

### Schema Definition (schemas.py)

```python
class DBTTransformationResponse(BaseModel):
    transformation_id: str = Field(..., description="Unique identifier for the transformation")
    name: str = Field(..., description="Name of the transformation")
    status: TransformationStatus = Field(..., description="Current status of the transformation")
    # ... other fields
```

### Service Code (service.py - BEFORE)

```python
transformation_data = {
    "id": transformation_id,  # ❌ Wrong field name
    "name": request.name,
    # ... other fields
}
```

## ✅ Fix Applied

**File:** `app/dbt_transformations/service.py`  
**Line:** 112  
**Change:** Renamed dictionary key from `"id"` to `"transformation_id"`

```python
transformation_data = {
    "transformation_id": transformation_id,  # ✅ Correct field name
    "name": request.name,
    # ... other fields
}
```

## 🚀 Deployment

Run the deployment script:

```bash
./deploy-schema-fix.sh
```

Or manually:

```bash
# Build
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:schema-fix .

# Push
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:schema-fix

# Deploy
helm upgrade --install asgard ./helmchart \
  --namespace asgard \
  --set image.tag=schema-fix \
  --wait
```

## 🧪 Testing

After deployment, test with:

```bash
curl -X 'POST' \
  'http://51.89.225.64/dbt/transform' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "test_transformation",
  "sql_query": "SELECT order_id, product_id, produced_units, operator_name, production_week FROM iceberg.silver.t2c60d13e WHERE produced_units > 0 LIMIT 20",
  "description": "Test transformation",
  "materialization": "table",
  "tags": ["test"],
  "owner": "dbt"
}'
```

## 📊 Expected Response

After the fix, you should receive:

```json
{
  "transformation_id": "uuid-here",
  "name": "test_transformation",
  "status": "completed",
  "created_at": "2025-10-07T...",
  "updated_at": "2025-10-07T...",
  "gold_table_name": "gold.test_transformation",
  "row_count": 20,
  "execution_time_seconds": 2.5,
  "description": "Test transformation",
  "tags": ["test"],
  "owner": "dbt"
}
```

## 🔗 Related Files

- `app/dbt_transformations/service.py` - Fixed transformation_id field
- `app/dbt_transformations/schemas.py` - Schema definition (unchanged)
- `app/dbt_transformations/router.py` - API endpoint (unchanged)

## 📝 Notes

This was a simple field name mismatch between the internal dictionary representation and the Pydantic response model. The service was working correctly, but the response validation was failing because the field name didn't match the schema definition.
