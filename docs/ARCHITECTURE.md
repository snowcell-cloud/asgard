# Asgard Platform - Technical Architecture# Feast Feature Store - Iceberg Integration Architecture

**Complete System Architecture & Design** ## 🏗️ Overview

**Last Updated:** November 11, 2025

**Version:** 1.0This Feast implementation leverages **Iceberg's native S3 Parquet storage** directly, eliminating the need for data duplication or synchronization.

---## 📊 Architecture Diagram

## 📋 Table of Contents```

┌───────────────────────────────────────────────────────────────┐

1. [Architecture Overview](#architecture-overview)│ Iceberg Tables (Gold Layer) │

2. [Technology Stack](#technology-stack)│ ┌──────────────────────────────────────────────────────┐ │

3. [Component Design](#component-design)│ │ S3 Storage │ │

4. [Data Flow Architecture](#data-flow-architecture)│ │ s3://airbytedestination1/iceberg/gold/ │ │

5. [Iceberg Integration](#iceberg-integration)│ │ │ │

6. [Feast Feature Store](#feast-feature-store)│ │ {table_id}/ │ │

7. [MLflow Integration](#mlflow-integration)│ │ ├── data/ │ │

8. [Security & Access Control](#security--access-control)│ │ │ ├── file1.parquet │ │

9. [Scalability & Performance](#scalability--performance)│ │ │ ├── file2.parquet │ │

10. [Design Decisions](#design-decisions)│ │ │ └── ... │ │

│ │ └── metadata/ │ │

---│ │ ├── snap-xxx.avro │ │

│ │ └── v1.metadata.json │ │

## Architecture Overview│ └──────────────────────────────────────────────────────┘ │

│ │

### High-Level System Design│ Managed by: Nessie (version control) │

└────────────────────────┬──────────────────────────────────────┘

Asgard is a **unified data lakehouse platform** built on Kubernetes that orchestrates the complete data lifecycle from ingestion to ML deployment through a single FastAPI gateway. │

                         │ Query & Validate

````↓

┌─────────────────────────────────────────────────────────────┐┌───────────────────────────────────────────────────────────────┐

│                    ASGARD PLATFORM                           ││  Trino Query Engine                                           │

│               (Kubernetes-Native Architecture)               ││  - Validates table exists in catalog                          │

└─────────────────────────────────────────────────────────────┘│  - Returns metadata including S3 file paths                   │

│  - Enables SQL queries on Iceberg tables                      │

┌─────────────────────────────────────────────────────────────┐└────────────────────────┬──────────────────────────────────────┘

│                   API LAYER (FastAPI)                        │                         │

│         http://asgard-app:80 (Internal Service)             │                         │ Get S3 Parquet Path

│                                                               │                         ↓

│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │┌───────────────────────────────────────────────────────────────┐

│  │ Airbyte  │  Spark   │   DBT    │  Feast   │  MLOps   │   ││  Feast FeatureStoreService                                    │

│  │  Router  │  Router  │  Router  │  Router  │  Router  │   ││  ┌─────────────────────────────────────────────────────┐     │

│  └─────┬────┴─────┬────┴─────┬────┴─────┬────┴─────┬────┘   ││  │  _get_iceberg_parquet_path()                        │     │

└────────┼──────────┼──────────┼──────────┼──────────┼────────┘│  │  - Queries Trino for table metadata                 │     │

         │          │          │          │          ││  │  - Extracts S3 path from $path column              │     │

         ▼          ▼          ▼          ▼          ▼│  │  - Returns: s3://bucket/iceberg/gold/.../data/*.parquet  │

┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│  └─────────────────────────────────────────────────────┘     │

│  AIRBYTE   │ │   SPARK    │ │    DBT     │ │   FEAST    ││                                                                │

│  Platform  │ │ K8s Operator│ │  + Trino   │ │Feature Store││  ┌─────────────────────────────────────────────────────┐     │

│            │ │            │ │            │ │            ││  │  create_feature_view()                              │     │

│ - Sources  │ │ - Driver   │ │ - SQL      │ │ - Registry ││  │  - Creates Feast FileSource with S3 path            │     │

│ - Sinks    │ │ - Executors│ │ - Models   │ │ - Offline  ││  │  - NO data copy/sync required                       │     │

│ - Sync Jobs│ │ - Jobs     │ │ - Tests    │ │   Store    ││  │  - Registers feature view with Feast                │     │

└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘│  └─────────────────────────────────────────────────────┘     │

      │              │              │              │└────────────────────────┬──────────────────────────────────────┘

      │ Write        │ Read/Write   │ Read/Write   │ Read                         │

      ▼              ▼              ▼              ▼                         │ FileSource(path=s3://...)

┌──────────────────────────────────────────────────────────────┐                         ↓

│           DATA LAKEHOUSE (Apache Iceberg + S3)               │┌───────────────────────────────────────────────────────────────┐

│                                                               ││  Feast Offline Store                                          │

│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   ││  - Type: file                                                 │

│  │ BRONZE LAYER │───▶│ SILVER LAYER │───▶│  GOLD LAYER  │   ││  - Reads directly from S3 Parquet files                       │

│  │  (Raw Data)  │    │  (Cleaned)   │    │ (Aggregated) │   ││  - No local storage required                                  │

│  │              │    │              │    │              │   ││  - Supports batch predictions                                 │

│  │ - customers  │    │ - customers_ │    │ - customer_  │   ││  - Historical feature retrieval                               │

│  │ - transactions│   │   cleaned    │    │   metrics    │   │└───────────────────────────────────────────────────────────────┘

│  │ - support    │    │ - transactions│   │ - churn_     │   │```

│  │   _tickets   │    │   _cleaned   │    │   predictions│   │

│  │              │    │              │    │              │   │## 🔑 Key Benefits

│  │ Format: Parquet (Snappy compression)                 │   │

│  │ Catalog: Nessie (Git-like data versioning)           │   │### 1. **Zero Data Duplication**

│  │ Storage: S3 (s3://airbytedestination1/iceberg/)      │   │

│  └──────────────┘    └──────────────┘    └──────────────┘   │- **Before**: Iceberg → Trino → Local Parquet → Feast

└──────────────────────────────────────────────────────────────┘- **Now**: Iceberg S3 Parquet → Feast (direct read)

         │- **Savings**: Eliminates local storage requirements and sync overhead

         ▼

┌──────────────────────────────────────────────────────────────┐### 2. **Single Source of Truth**

│                    ML PLATFORM (MLflow)                       │

│                                                               │- Feast reads the same Parquet files that Iceberg manages

│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │- No synchronization lag or data consistency issues

│  │  Tracking   │───▶│   Model     │───▶│  Inference  │     │- Updates to Iceberg tables are immediately available to Feast

│  │   Server    │    │  Registry   │    │   Service   │     │

│  │             │    │             │    │             │     │### 3. **Scalability**

│  │ - Experiments│   │ - Models    │    │ - REST API  │     │

│  │ - Metrics   │    │ - Versions  │    │ - Batch     │     │- S3 provides infinite storage capacity

│  │ - Artifacts │    │ - Staging   │    │ - Real-time │     │- No local disk space limitations

│  └─────────────┘    └─────────────┘    └─────────────┘     │- Leverages Iceberg's optimized Parquet file layout

│                                                               │

│  Backend: PostgreSQL (metadata)                              │### 4. **Cost Efficiency**

│  Artifacts: S3 (models, logs)                                │

└──────────────────────────────────────────────────────────────┘- No duplicate storage costs

```- Reduced network transfer (no data copying)

- Utilizes existing S3 infrastructure

### Key Architectural Principles

## 📂 Data Path Structure

1. **API-First Design** - All operations accessible via REST API

2. **Medallion Architecture** - Bronze → Silver → Gold data layers### Iceberg Storage Format

3. **Zero Data Duplication** - Feast reads directly from Iceberg S3 Parquet

4. **Kubernetes Native** - Cloud-agnostic, scalable deployment```

5. **Separation of Concerns** - Each component has a single responsibilitys3://airbytedestination1/iceberg/gold/

6. **Event-Driven** - Asynchronous job execution with status tracking├── {table_id}/

│   ├── data/

---│   │   ├── 20251007_082213_00049_yb5wr-{uuid}.parquet

│   │   ├── 20251007_083145_00051_yb5wr-{uuid}.parquet

## Technology Stack│   │   └── ...

│   └── metadata/

### Core Components│       ├── snap-1234567890.avro

│       ├── v1.metadata.json

| Layer | Component | Version | Purpose |│       ├── v2.metadata.json

|-------|-----------|---------|---------|│       └── ...

| **API Gateway** | FastAPI | 0.104+ | REST API server |```

| **Data Ingestion** | Airbyte | OSS | CDC and data connectors |

| **Data Processing** | Apache Spark | 3.5.0 | Distributed data processing |### Feast FileSource Configuration

| **SQL Transform** | DBT + Trino | 1.6+ / 428+ | SQL-based transformations |

| **Feature Store** | Feast | 0.35+ | Feature management |```python

| **ML Platform** | MLflow | 2.16.2 | Experiment tracking & registry |FileSource(

| **Data Lakehouse** | Apache Iceberg | 1.5+ | Table format |    name="customer_features_source",

| **Data Catalog** | Project Nessie | 0.74+ | Version control for data |    path="s3://airbytedestination1/iceberg/gold/{table_id}/data/*.parquet",

| **Object Storage** | AWS S3 | - | Data and artifact storage |    timestamp_field="event_timestamp",

| **Metadata DB** | PostgreSQL | 13+ | MLflow backend, Feast registry |)

| **Orchestration** | Kubernetes | 1.27+ | Container orchestration |```

| **Spark Operator** | Spark on K8s | 3.5.0 | Spark job management |

## 🔄 Data Flow

### Language & Frameworks

### Feature Registration Flow

| Technology | Version | Usage |

|------------|---------|-------|1. **User Request**: POST /feast/features with Iceberg table name

| **Python** | 3.11 | Primary language for all services |2. **Table Validation**: Query Trino to ensure table exists

| **PySpark** | 3.5.0 | Spark transformations |3. **Path Discovery**: Extract S3 Parquet path from Iceberg metadata

| **SQL** | - | DBT models, Trino queries |4. **Feature View Creation**: Register Feast FileSource with S3 path

| **YAML** | - | Configuration, Kubernetes manifests |5. **Ready to Use**: Features available for training/predictions

| **Parquet** | - | Data storage format |

### Batch Prediction Flow

---

1. **Feature Request**: Specify entity IDs and feature views

## Component Design2. **S3 Read**: Feast reads Parquet files directly from S3

3. **Feature Computation**: Apply transformations if needed

### 1. FastAPI Gateway4. **Return Results**: Feature values for requested entities



**Purpose**: Unified REST API for all platform operations## ⚙️ Configuration



**Architecture**:### Environment Variables



```python```bash

app/# S3/Iceberg Configuration

├── __init__.pyS3_BUCKET=airbytedestination1

├── main.py               # FastAPI applicationS3_ICEBERG_BASE_PATH=iceberg/gold

├── config.py             # Configuration managementAWS_ACCESS_KEY_ID=your_access_key

│AWS_SECRET_ACCESS_KEY=your_secret_key

├── airbyte/              # Airbyte integrationAWS_REGION=us-east-1

│   ├── router.py         # API endpoints

│   ├── schemas.py        # Pydantic models# Trino Configuration

│   └── client.py         # Airbyte API clientTRINO_HOST=trino.data-platform.svc.cluster.local

│TRINO_PORT=8080

├── data_transformation/  # Spark integrationTRINO_USER=dbt

│   ├── router.pyTRINO_CATALOG=iceberg

│   ├── schemas.pyGOLD_SCHEMA=gold

│   ├── client.py         # Spark Operator client

│   └── service.py        # Business logic# Feast Configuration

│FEAST_REPO_PATH=/tmp/feast_repo

├── dbt_transformations/  # DBT integration```

│   ├── router.py

│   ├── schemas.py### feature_store.yaml

│   └── service.py        # DBT + Trino orchestration

│```yaml

├── feast/                # Feast integrationproject: asgard_features

│   ├── router.pyregistry: /tmp/feast_repo/registry.db

│   ├── schemas.pyprovider: local

│   └── service.py        # Feature store operationsoffline_store:

│  type: file

├── mlops/                # MLOps integration  # Reads directly from S3 Parquet files created by Iceberg

│   ├── router.pyentity_key_serialization_version: 2

│   ├── schemas.py```

│   ├── service.py        # Training orchestration

│   └── deployment_service.py  # Inference serving## 🔍 Implementation Details

│

└── data_products/        # Direct data access### Method: `_get_iceberg_parquet_path()`

    ├── router.py

    ├── schemas.py```python

    └── client.py         # Trino clientdef _get_iceberg_parquet_path(self, table_fqn: str) -> str:

```    """

    Query Trino to get the S3 Parquet file path from Iceberg table.

**Key Features**:

- **OpenAPI/Swagger** - Auto-generated API documentation    Uses the $path system column to extract actual file locations.

- **Pydantic Validation** - Type-safe request/response models    Returns: s3://bucket/iceberg/gold/{table_id}/data/*.parquet

- **Async Support** - Non-blocking I/O for better performance    """

- **Dependency Injection** - Clean separation of concerns```

- **Error Handling** - Standardized error responses

**Query Example**:

### 2. Airbyte Platform

```sql

**Purpose**: Data ingestion from external sources to Bronze layerSELECT "$path" as file_path

FROM iceberg.gold.customer_aggregates

**Components**:LIMIT 1

- **Server**: Airbyte OSS server```

- **Workers**: Execute sync jobs

- **Temporal**: Workflow orchestration**Result**:

- **Database**: PostgreSQL for metadata

````

**Data Flow**:s3://airbytedestination1/iceberg/gold/efxgs5oersyezxnzydx4vsyou04jna6ti5-3b47231ef3b04d2ea373644a18f34c23/data/20251007_082213_00049_yb5wr-4e34e6e9-1b01-4ab5-a0fa-fc3e6ce21ed0.parquet

```

```

Source DB → Airbyte Connector → Normalization → S3/Iceberg (Bronze)**Extracted Path**:

```

```

**Supported Sources**:s3://airbytedestination1/iceberg/gold/efxgs5oersyezxnzydx4vsyou04jna6ti5-3b47231ef3b04d2ea373644a18f34c23/data/\*.parquet

- PostgreSQL```

- MySQL

- MongoDB## 📊 Comparison: Old vs New Approach

- REST APIs

- File sources (CSV, JSON)| Aspect | Old Approach | New Approach |

| ----------------- | --------------------------- | ------------------------ |

### 3. Spark on Kubernetes| **Data Storage** | Duplicate (Iceberg + Local) | Single (Iceberg S3 only) |

| **Sync Required** | Yes (Trino → Local) | No (direct S3 read) |

**Purpose**: Distributed data processing (Bronze → Silver)| **Latency** | Higher (copy overhead) | Lower (direct access) |

| **Storage Cost** | 2x (Iceberg + Local) | 1x (Iceberg only) |

**Architecture**:| **Consistency** | Eventual (after sync) | Immediate (same files) |

| **Scalability** | Limited by local disk | Unlimited (S3) |

````| **Complexity**    | Higher (sync logic)         | Lower (direct read)      |

┌─────────────────────────────────────────────┐

│        Spark Operator (K8s Custom Resource)  │## 🚀 Usage Example

└─────────────────────────────────────────────┘

                    │```python

                    ▼# Register features from Iceberg table

┌─────────────────────────────────────────────┐POST /feast/features

│          SparkApplication                    │{

│  apiVersion: sparkoperator.k8s.io/v1beta2   │  "name": "customer_features",

│  kind: SparkApplication                     │  "entities": ["customer_id"],

└─────────────────────────────────────────────┘  "features": [

                    │    {"name": "total_orders", "dtype": "int64"},

        ┌───────────┴───────────┐    {"name": "avg_order_value", "dtype": "float64"}

        ▼                       ▼  ],

┌──────────────┐       ┌──────────────┐  "source": {

│ Driver Pod   │       │ Executor Pods│    "catalog": "iceberg",

│              │       │              │    "schema": "gold",

│ - Spark SQL  │       │ - Data       │    "table_name": "customer_aggregates",

│ - Job logic  │       │   processing │    "timestamp_field": "updated_at"

│ - Coordinator│       │ - Parallel   │  },

└──────────────┘       │   execution  │  "online": false

                       └──────────────┘}

````

# Response

**Key Capabilities**:{

- **SQL-based transformations** via Spark SQL "name": "customer_features",

- **Iceberg integration** for reading/writing tables "source_table": "iceberg.gold.customer_aggregates",

- **Dynamic resource allocation** "message": "Feature view 'customer_features' successfully registered from Iceberg gold layer with 2 features (offline store only)"

- **Auto-scaling** executors based on workload}

- **Job monitoring** via Spark UI```

### 4. DBT + Trino## 🔐 Security & Access

**Purpose**: SQL-based business logic transformations (Silver → Gold)- **S3 Access**: Uses AWS credentials (IAM roles or access keys)

- **Trino Access**: Authenticates with Trino for metadata queries

**Architecture**:- **Nessie**: Iceberg metadata version control (if enabled)

- **Encryption**: Supports S3 encryption at rest

````

┌─────────────────────────────────────────────┐## 📈 Performance Considerations

│            DBT Service                       │

│  - Receives SQL model definitions           │1. **S3 Read Performance**:

│  - Generates Trino queries                  │   - Parquet columnar format optimized for analytics

│  - Executes via Trino client                │   - Iceberg partition pruning reduces data scanned

└─────────────────────────────────────────────┘2. **Network Bandwidth**:

                    │

                    ▼   - Direct S3 reads within same AWS region

┌─────────────────────────────────────────────┐   - Minimize cross-region transfers

│            Trino Query Engine                │

│  - Distributed SQL engine                   │3. **Caching**:

│  - Iceberg connector                        │   - Feast can cache feature metadata

│  - Nessie catalog integration               │   - S3 objects can be cached by clients

└─────────────────────────────────────────────┘

                    │## 🛠️ Maintenance

                    ▼

┌─────────────────────────────────────────────┐### Data Updates

│         Iceberg Tables (Silver/Gold)         │

└─────────────────────────────────────────────┘- Iceberg handles data updates with ACID transactions

```- New Parquet files automatically picked up by Feast

- No manual sync or refresh required

**Key Features**:

- **SQL-first** approach for data transformations### Schema Evolution

- **Incremental models** for efficient processing

- **Testing framework** for data quality- Iceberg supports schema evolution

- **Documentation** generation- Update Feast feature views when schema changes

- **Lineage tracking**- Re-register feature view with updated schema



### 5. Feast Feature Store## 📚 References



**Purpose**: Feature management for ML workflows- [Apache Iceberg Documentation](https://iceberg.apache.org/)

- [Feast File Offline Store](https://docs.feast.dev/reference/offline-stores/file)

**Architecture**:- [Nessie Documentation](https://projectnessie.org/)

- [AWS S3 Parquet Best Practices](https://docs.aws.amazon.com/athena/latest/ug/columnar-storage.html)

````

┌─────────────────────────────────────────────┐
│ Feast Feature Store │
│ │
│ ┌────────────────────────────────────┐ │
│ │ Feature Registry (PostgreSQL) │ │
│ │ - Feature views │ │
│ │ - Entities │ │
│ │ - Feature services │ │
│ └────────────────────────────────────┘ │
│ │
│ ┌────────────────────────────────────┐ │
│ │ Offline Store (File) │ │
│ │ - Reads S3 Parquet directly │ │
│ │ - Historical feature retrieval │ │
│ │ - NO data duplication │ │
│ └────────────────────────────────────┘ │
└─────────────────────────────────────────────┘

```

**Unique Design**: Direct S3 Parquet reads from Iceberg Gold layer (see [FEAST_ICEBERG_ARCHITECTURE.md](FEAST_ICEBERG_ARCHITECTURE.md))

### 6. MLflow Platform

**Purpose**: ML experiment tracking, model registry, and serving

**Components**:

```

┌─────────────────────────────────────────────┐
│ MLflow Tracking Server │
│ - Experiment tracking │
│ - Metric logging │
│ - Artifact storage │
└─────────────────────────────────────────────┘
│
┌───────────┴───────────┐
▼ ▼
┌──────────────┐ ┌──────────────┐
│ PostgreSQL │ │ S3 │
│ (Metadata) │ │ (Artifacts) │
│ │ │ │
│ - Runs │ │ - Models │
│ - Params │ │ - Plots │
│ - Metrics │ │ - Logs │
└──────────────┘ └──────────────┘

```

**Model Lifecycle**:

```

Training Script → MLflow Tracking → Model Registry → Model Serving
│ │ │ │
↓ ↓ ↓ ↓
Upload Log metrics Version model Inference API

```

---

## Data Flow Architecture

### Medallion Architecture

The platform implements a **medallion architecture** with three data layers:

#### Bronze Layer (Raw Data)

- **Source**: Airbyte ingestion
- **Format**: Parquet (as-is from source)
- **Purpose**: Historical data preservation
- **Retention**: Indefinite
- **Schema**: Source schema (no transformations)

```

s3://airbytedestination1/iceberg/bronze/
├── customers/
│ ├── data/
│ │ └── \*.parquet
│ └── metadata/
├── transactions/
└── support_tickets/

```

#### Silver Layer (Cleaned Data)

- **Source**: Spark transformations from Bronze
- **Format**: Parquet (Snappy compression)
- **Purpose**: Clean, validated, deduplicated data
- **Operations**: Type casting, null handling, validation
- **Schema**: Standardized schema

```

s3://airbytedestination1/iceberg/silver/
├── customers_cleaned/
├── transactions_cleaned/
└── support_tickets_cleaned/

```

#### Gold Layer (Business Metrics)

- **Source**: DBT transformations from Silver
- **Format**: Parquet (Snappy compression)
- **Purpose**: Business-level aggregations and metrics
- **Operations**: Joins, aggregations, feature engineering
- **Schema**: ML-ready features

```

s3://airbytedestination1/iceberg/gold/
├── customer_metrics/
├── product_analytics/
└── churn_predictions/

```

### End-to-End Data Flow

```

External DBs/APIs
│
├─ Airbyte Sync ─────────────────▶ Bronze Layer
│ (Raw data)
│ │
│ │
│ Spark SQL
│ (Cleansing)
│ │
│ ▼
│ Silver Layer
│ (Clean data)
│ │
│ │
│ DBT + Trino
│ (Aggregation)
│ │
│ ▼
│ Gold Layer
│ (Metrics)
│ │
│ │
│ Feast Register
│ (Feature View)
│ │
│ ▼
│ Feature Store
│ (S3 Parquet)
│ │
│ │
│ ML Training
│ (MLflow)
│ │
│ ▼
│ Model Registry
│ │
│ │
│ Model Serving
│ │
│ ▼
└──────────────────────────────▶ Predictions/Actions

```

---

## Iceberg Integration

### Why Iceberg?

1. **ACID Transactions** - Consistent reads and writes
2. **Time Travel** - Query data at any point in time
3. **Schema Evolution** - Add/modify columns without breaking queries
4. **Hidden Partitioning** - Automatic partition management
5. **Compaction** - Optimize small files automatically
6. **Metadata Efficiency** - Fast query planning

### Iceberg + Nessie Architecture

```

┌─────────────────────────────────────────────┐
│ Nessie Catalog Server │
│ (Git-like version control for data) │
│ │
│ - Branches (dev, staging, prod) │
│ - Commits (data snapshots) │
│ - Tags (data releases) │
│ - Merge (environment promotion) │
└─────────────────────────────────────────────┘
│
│ Catalog API
▼
┌─────────────────────────────────────────────┐
│ Iceberg Table Metadata │
│ │
│ metadata/ │
│ ├── v1.metadata.json (schema, partitions) │
│ ├── v2.metadata.json (new snapshot) │
│ └── snap-123.avro (snapshot manifest) │
└─────────────────────────────────────────────┘
│
│ Points to
▼
┌─────────────────────────────────────────────┐
│ Data Files (S3) │
│ │
│ data/ │
│ ├── file1.parquet │
│ ├── file2.parquet │
│ └── file3.parquet │
└─────────────────────────────────────────────┘

````

### Table Operations

```sql
-- Create table
CREATE TABLE iceberg.silver.customers (
  customer_id BIGINT,
  email VARCHAR,
  registration_date DATE
)
WITH (
  format = 'PARQUET',
  partitioning = ARRAY['registration_date']
);

-- Time travel query
SELECT * FROM iceberg.silver.customers
FOR TIMESTAMP AS OF TIMESTAMP '2025-11-01 00:00:00';

-- Schema evolution
ALTER TABLE iceberg.silver.customers
ADD COLUMN loyalty_tier VARCHAR;
````

---

## Feast Feature Store

### Zero-Duplication Design

Traditional approach (with duplication):

```
Iceberg Gold → Export to Parquet → Copy to Feast → Feature Store
```

Asgard approach (zero duplication):

```
Iceberg Gold (S3 Parquet) ← Feast reads directly (FileSource)
```

**Implementation**:

```python
# Get S3 path from Iceberg table
parquet_path = _get_iceberg_parquet_path("iceberg.gold.customer_metrics")
# Returns: s3://bucket/iceberg/gold/{table_id}/data/*.parquet

# Create Feast FileSource pointing to Iceberg S3 path
source = FileSource(
    name="customer_metrics_source",
    path=parquet_path,
    timestamp_field="updated_at"
)

# Register feature view
feature_view = FeatureView(
    name="customer_churn_features",
    entities=[customer],
    schema=features,
    source=source
)
```

For complete details, see [FEAST_ICEBERG_ARCHITECTURE.md](FEAST_ICEBERG_ARCHITECTURE.md)

---

## MLflow Integration

### Training Workflow

```
Training Script Upload
      │
      ▼
Job Execution Pod
      │
      ├─ Install dependencies
      ├─ Fetch features from Feast
      ├─ Train model
      ├─ Log metrics to MLflow
      └─ Register model
            │
            ▼
      MLflow Model Registry
            │
            ▼
      Model Serving (Inference API)
```

### Model Versioning

```
customer_churn_predictor
├── v1 (Staging)
│   ├── metrics: {accuracy: 0.85}
│   └── artifacts: model.pkl
├── v2 (Production)
│   ├── metrics: {accuracy: 0.87}
│   └── artifacts: model.pkl
└── v3 (Development)
    ├── metrics: {accuracy: 0.89}
    └── artifacts: model.pkl
```

---

## Security & Access Control

### Authentication & Authorization

```
┌─────────────────────────────────────────────┐
│         Kubernetes RBAC                      │
│  - ServiceAccounts                           │
│  - Roles & RoleBindings                     │
│  - Network Policies                         │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         AWS IAM (for S3 access)              │
│  - Access keys stored in K8s secrets        │
│  - IAM roles for pod identities (IRSA)      │
└─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│         Application-Level Security           │
│  - API key validation (if enabled)          │
│  - Request throttling                       │
│  - Input validation (Pydantic)              │
└─────────────────────────────────────────────┘
```

### Data Security

- **Encryption at Rest**: S3 server-side encryption (SSE-S3 or SSE-KMS)
- **Encryption in Transit**: TLS for all service communication
- **Access Control**: IAM policies for S3, Kubernetes RBAC for services
- **Secrets Management**: Kubernetes secrets for credentials

---

## Scalability & Performance

### Horizontal Scaling

| Component   | Scaling Strategy                  |
| ----------- | --------------------------------- |
| **FastAPI** | Kubernetes HPA (CPU-based)        |
| **Spark**   | Dynamic executor allocation       |
| **Trino**   | Worker pool expansion             |
| **Airbyte** | Worker replicas                   |
| **MLflow**  | Stateless deployment (scale pods) |

### Performance Optimizations

1. **Iceberg Compaction**: Merge small files automatically
2. **Spark Caching**: In-memory data for iterative processing
3. **Trino Query Optimization**: Predicate pushdown, partition pruning
4. **S3 Transfer Acceleration**: Faster uploads/downloads
5. **Connection Pooling**: Reuse database connections

---

## Design Decisions

### Why FastAPI?

- **Performance**: Async support for high throughput
- **Type Safety**: Pydantic validation
- **Auto Documentation**: OpenAPI/Swagger generation
- **Modern Python**: Python 3.11+ features

### Why Iceberg over Delta/Hudi?

- **Vendor Neutral**: Not tied to Spark/Databricks
- **Nessie Integration**: Git-like versioning
- **Hidden Partitioning**: Simplifies queries
- **Strong Community**: Apache foundation

### Why Feast for Features?

- **Simplicity**: Easy to define features
- **Flexibility**: Multiple offline/online stores
- **ML Framework Agnostic**: Works with any ML library
- **Direct S3 Read**: No data duplication

### Why Kubernetes?

- **Cloud Agnostic**: Run anywhere (EKS, GKE, on-prem)
- **Auto Scaling**: HPA, VPA, cluster autoscaler
- **Service Discovery**: Built-in DNS
- **Resource Management**: CPU/memory limits and requests

---

## Summary

### Key Architectural Highlights

1. ✅ **Unified API** - Single entry point for all operations
2. ✅ **Zero Duplication** - Feast reads directly from Iceberg
3. ✅ **Medallion Architecture** - Bronze → Silver → Gold
4. ✅ **Kubernetes Native** - Cloud-agnostic, scalable
5. ✅ **Open Source** - No vendor lock-in
6. ✅ **Production Ready** - Battle-tested components

### Next Steps

- **Learn the workflow**: [USE_CASE_GUIDE.md](USE_CASE_GUIDE.md)
- **Test the APIs**: [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
- **Visualize the system**: [DIAGRAMS.md](DIAGRAMS.md)
- **Troubleshoot issues**: [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
