# Feast Feature Store - Iceberg Integration Architecture

## 🏗️ Overview

This Feast implementation leverages **Iceberg's native S3 Parquet storage** directly, eliminating the need for data duplication or synchronization.

## 📊 Architecture Diagram

```
┌───────────────────────────────────────────────────────────────┐
│  Iceberg Tables (Gold Layer)                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  S3 Storage                                           │    │
│  │  s3://airbytedestination1/iceberg/gold/               │    │
│  │                                                        │    │
│  │  {table_id}/                                          │    │
│  │    ├── data/                                          │    │
│  │    │   ├── file1.parquet                             │    │
│  │    │   ├── file2.parquet                             │    │
│  │    │   └── ...                                        │    │
│  │    └── metadata/                                      │    │
│  │        ├── snap-xxx.avro                             │    │
│  │        └── v1.metadata.json                          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
│  Managed by: Nessie (version control)                         │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ Query & Validate
                         ↓
┌───────────────────────────────────────────────────────────────┐
│  Trino Query Engine                                           │
│  - Validates table exists in catalog                          │
│  - Returns metadata including S3 file paths                   │
│  - Enables SQL queries on Iceberg tables                      │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ Get S3 Parquet Path
                         ↓
┌───────────────────────────────────────────────────────────────┐
│  Feast FeatureStoreService                                    │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  _get_iceberg_parquet_path()                        │     │
│  │  - Queries Trino for table metadata                 │     │
│  │  - Extracts S3 path from $path column              │     │
│  │  - Returns: s3://bucket/iceberg/gold/.../data/*.parquet  │
│  └─────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  create_feature_view()                              │     │
│  │  - Creates Feast FileSource with S3 path            │     │
│  │  - NO data copy/sync required                       │     │
│  │  - Registers feature view with Feast                │     │
│  └─────────────────────────────────────────────────────┘     │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ FileSource(path=s3://...)
                         ↓
┌───────────────────────────────────────────────────────────────┐
│  Feast Offline Store                                          │
│  - Type: file                                                 │
│  - Reads directly from S3 Parquet files                       │
│  - No local storage required                                  │
│  - Supports batch predictions                                 │
│  - Historical feature retrieval                               │
└───────────────────────────────────────────────────────────────┘
```

## 🔑 Key Benefits

### 1. **Zero Data Duplication**

- **Before**: Iceberg → Trino → Local Parquet → Feast
- **Now**: Iceberg S3 Parquet → Feast (direct read)
- **Savings**: Eliminates local storage requirements and sync overhead

### 2. **Single Source of Truth**

- Feast reads the same Parquet files that Iceberg manages
- No synchronization lag or data consistency issues
- Updates to Iceberg tables are immediately available to Feast

### 3. **Scalability**

- S3 provides infinite storage capacity
- No local disk space limitations
- Leverages Iceberg's optimized Parquet file layout

### 4. **Cost Efficiency**

- No duplicate storage costs
- Reduced network transfer (no data copying)
- Utilizes existing S3 infrastructure

## 📂 Data Path Structure

### Iceberg Storage Format

```
s3://airbytedestination1/iceberg/gold/
├── {table_id}/
│   ├── data/
│   │   ├── 20251007_082213_00049_yb5wr-{uuid}.parquet
│   │   ├── 20251007_083145_00051_yb5wr-{uuid}.parquet
│   │   └── ...
│   └── metadata/
│       ├── snap-1234567890.avro
│       ├── v1.metadata.json
│       ├── v2.metadata.json
│       └── ...
```

### Feast FileSource Configuration

```python
FileSource(
    name="customer_features_source",
    path="s3://airbytedestination1/iceberg/gold/{table_id}/data/*.parquet",
    timestamp_field="event_timestamp",
)
```

## 🔄 Data Flow

### Feature Registration Flow

1. **User Request**: POST /feast/features with Iceberg table name
2. **Table Validation**: Query Trino to ensure table exists
3. **Path Discovery**: Extract S3 Parquet path from Iceberg metadata
4. **Feature View Creation**: Register Feast FileSource with S3 path
5. **Ready to Use**: Features available for training/predictions

### Batch Prediction Flow

1. **Feature Request**: Specify entity IDs and feature views
2. **S3 Read**: Feast reads Parquet files directly from S3
3. **Feature Computation**: Apply transformations if needed
4. **Return Results**: Feature values for requested entities

## ⚙️ Configuration

### Environment Variables

```bash
# S3/Iceberg Configuration
S3_BUCKET=airbytedestination1
S3_ICEBERG_BASE_PATH=iceberg/gold
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Trino Configuration
TRINO_HOST=trino.data-platform.svc.cluster.local
TRINO_PORT=8080
TRINO_USER=dbt
TRINO_CATALOG=iceberg
GOLD_SCHEMA=gold

# Feast Configuration
FEAST_REPO_PATH=/tmp/feast_repo
```

### feature_store.yaml

```yaml
project: asgard_features
registry: /tmp/feast_repo/registry.db
provider: local
offline_store:
  type: file
  # Reads directly from S3 Parquet files created by Iceberg
entity_key_serialization_version: 2
```

## 🔍 Implementation Details

### Method: `_get_iceberg_parquet_path()`

```python
def _get_iceberg_parquet_path(self, table_fqn: str) -> str:
    """
    Query Trino to get the S3 Parquet file path from Iceberg table.

    Uses the $path system column to extract actual file locations.
    Returns: s3://bucket/iceberg/gold/{table_id}/data/*.parquet
    """
```

**Query Example**:

```sql
SELECT "$path" as file_path
FROM iceberg.gold.customer_aggregates
LIMIT 1
```

**Result**:

```
s3://airbytedestination1/iceberg/gold/efxgs5oersyezxnzydx4vsyou04jna6ti5-3b47231ef3b04d2ea373644a18f34c23/data/20251007_082213_00049_yb5wr-4e34e6e9-1b01-4ab5-a0fa-fc3e6ce21ed0.parquet
```

**Extracted Path**:

```
s3://airbytedestination1/iceberg/gold/efxgs5oersyezxnzydx4vsyou04jna6ti5-3b47231ef3b04d2ea373644a18f34c23/data/*.parquet
```

## 📊 Comparison: Old vs New Approach

| Aspect            | Old Approach                | New Approach             |
| ----------------- | --------------------------- | ------------------------ |
| **Data Storage**  | Duplicate (Iceberg + Local) | Single (Iceberg S3 only) |
| **Sync Required** | Yes (Trino → Local)         | No (direct S3 read)      |
| **Latency**       | Higher (copy overhead)      | Lower (direct access)    |
| **Storage Cost**  | 2x (Iceberg + Local)        | 1x (Iceberg only)        |
| **Consistency**   | Eventual (after sync)       | Immediate (same files)   |
| **Scalability**   | Limited by local disk       | Unlimited (S3)           |
| **Complexity**    | Higher (sync logic)         | Lower (direct read)      |

## 🚀 Usage Example

```python
# Register features from Iceberg table
POST /feast/features
{
  "name": "customer_features",
  "entities": ["customer_id"],
  "features": [
    {"name": "total_orders", "dtype": "int64"},
    {"name": "avg_order_value", "dtype": "float64"}
  ],
  "source": {
    "catalog": "iceberg",
    "schema": "gold",
    "table_name": "customer_aggregates",
    "timestamp_field": "updated_at"
  },
  "online": false
}

# Response
{
  "name": "customer_features",
  "source_table": "iceberg.gold.customer_aggregates",
  "message": "Feature view 'customer_features' successfully registered from Iceberg gold layer with 2 features (offline store only)"
}
```

## 🔐 Security & Access

- **S3 Access**: Uses AWS credentials (IAM roles or access keys)
- **Trino Access**: Authenticates with Trino for metadata queries
- **Nessie**: Iceberg metadata version control (if enabled)
- **Encryption**: Supports S3 encryption at rest

## 📈 Performance Considerations

1. **S3 Read Performance**:
   - Parquet columnar format optimized for analytics
   - Iceberg partition pruning reduces data scanned
2. **Network Bandwidth**:

   - Direct S3 reads within same AWS region
   - Minimize cross-region transfers

3. **Caching**:
   - Feast can cache feature metadata
   - S3 objects can be cached by clients

## 🛠️ Maintenance

### Data Updates

- Iceberg handles data updates with ACID transactions
- New Parquet files automatically picked up by Feast
- No manual sync or refresh required

### Schema Evolution

- Iceberg supports schema evolution
- Update Feast feature views when schema changes
- Re-register feature view with updated schema

## 📚 References

- [Apache Iceberg Documentation](https://iceberg.apache.org/)
- [Feast File Offline Store](https://docs.feast.dev/reference/offline-stores/file)
- [Nessie Documentation](https://projectnessie.org/)
- [AWS S3 Parquet Best Practices](https://docs.aws.amazon.com/athena/latest/ug/columnar-storage.html)
