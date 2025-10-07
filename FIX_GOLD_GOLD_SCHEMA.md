# Fix: Schema Duplication Issue (gold_gold → gold)

## 🐛 Problem

Data was being created in schema `gold_gold` instead of `gold`.

## 🔍 Root Cause

**dbt's schema behavior:** When you specify a `schema` in the model config or dbt_project.yml, dbt **appends** it to the base schema from profiles.yml.

```
profiles.yml schema: "gold"
+ model config schema: "gold"
= Result: "gold_gold"
```

This happened in two places:

### 1. dbt_project.yml (Line 278)

```yaml
models:
  asgard_transformations:
    gold:
      +materialized: table
      +schema: gold # ❌ This causes duplication
```

### 2. Model Config Generation (Line 207)

```python
config = {
    "materialized": request.materialization.value,
    "schema": self.gold_schema,  # ❌ This also causes duplication
}
```

## ✅ Fixes Applied

### Fix 1: Removed `+schema: gold` from dbt_project.yml

**File:** `app/dbt_transformations/service.py`  
**Line:** 278 (removed)

```yaml
# BEFORE ❌
models:
  asgard_transformations:
    gold:
      +materialized: table
      +schema: gold

# AFTER ✅
models:
  asgard_transformations:
    gold:
      +materialized: table
```

### Fix 2: Removed schema from model config

**File:** `app/dbt_transformations/service.py`  
**Line:** 207

```python
# BEFORE ❌
config = {
    "materialized": request.materialization.value,
    "schema": self.gold_schema,
}

# AFTER ✅
config = {
    "materialized": request.materialization.value,
    # schema is already set in profiles.yml, don't duplicate it
}
```

## 📝 How dbt Schema Works

From dbt documentation:

1. **Base schema** is set in `profiles.yml` (`schema: gold`)
2. **Custom schema** in model config is **appended** to base schema
3. Example:
   - profiles.yml: `schema: gold`
   - model config: `schema: custom`
   - Result: `gold_custom`

To use just the base schema from profiles.yml, **don't set schema in model config**.

## 🚀 Deployment

```bash
# Build
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:fix-gold-schema .

# Push
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:fix-gold-schema

# Deploy
helm upgrade --install asgard ./helmchart \
  --namespace asgard \
  --set image.tag=fix-gold-schema \
  --wait
```

## 🧪 Testing

After deployment:

```bash
curl -X 'POST' \
  'http://51.89.225.64/dbt/transform' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "test_gold_schema",
  "sql_query": "SELECT order_id, product_id, produced_units FROM iceberg.silver.t2c60d13e WHERE produced_units > 0 LIMIT 10",
  "description": "Test correct schema",
  "materialization": "table",
  "owner": "dbt"
}'
```

### Expected Result

The table should be created in **`iceberg.gold.test_gold_schema`**, NOT `iceberg.gold_gold.test_gold_schema`.

You can verify with:

```sql
-- Check table exists in gold schema
SELECT * FROM iceberg.gold.test_gold_schema LIMIT 5;

-- Verify schema doesn't have gold_gold
SHOW SCHEMAS IN iceberg;
```

## 📊 Schema Structure

After the fix:

```
iceberg (catalog)
├── silver (schema)
│   └── t2c60d13e (table)
│   └── ... (other tables)
└── gold (schema)  ✅ Correct!
    └── test_gold_schema (table)
    └── ... (other transformations)

# NOT this ❌
iceberg
└── gold_gold (schema)  ❌ Wrong - should never exist
```

## 🔗 Related Files Modified

1. `app/dbt_transformations/service.py`
   - Line 207: Removed `"schema": self.gold_schema` from config dict
   - Line 278: Removed `+schema: gold` from dbt_project.yml template

## 📚 References

- [dbt Custom Schemas Documentation](https://docs.getdbt.com/docs/build/custom-schemas)
- dbt behavior: Custom schemas are **appended**, not replaced

## ✅ Validation Checklist

After deployment:

- [ ] Run transformation via API
- [ ] Verify table created in `iceberg.gold.{model_name}`
- [ ] Confirm no `gold_gold` schema exists
- [ ] Query the table successfully
- [ ] Check dbt logs show correct schema
