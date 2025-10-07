# Data Transformation APIs Documentation

## Overview

The Asgard Data Platform provides two complementary transformation APIs that enable data processing at different layers of the data lake architecture:

### **Spark Transformation API** (`/spark`)

Kubernetes-native, distributed Spark-based transformations for moving data from **Bronze → Silver** layers.

### **DBT Transformation API** (`/dbt`)

SQL-driven, dbt-powered transformations for moving data from **Silver → Gold** layers.

---

## Spark Transformation API

### Purpose

The Spark Transformation API executes distributed SQL transformations using Apache Spark on Kubernetes, primarily designed for:

- **Processing raw data** from the Bronze layer
- **Cleaning and standardizing data** for the Silver layer
- **Large-scale data transformations** requiring distributed computing
- **Complex data operations** like joins, aggregations, and window functions

### How It Works

#### Architecture Flow

```
Raw Data (Bronze) → Spark on Kubernetes → Processed Data (Silver)
      ↓                      ↓                        ↓
   S3 Bucket          SparkOperator            S3 Bucket
                    (Custom Resource)
```

#### Key Components

1. **SparkApplicationClient**: Manages Kubernetes SparkApplication custom resources
2. **TransformationService**: Orchestrates job submission and monitoring
3. **SparkOperator**: Kubernetes operator that runs Spark jobs as pods
4. **S3 Storage**: Reads from Bronze layer, writes to Silver layer

#### Process Flow

1. **API Request**: Client submits SQL transformation request

   ```json
   POST /spark/transform
   {
     "sql": "SELECT customer_id, SUM(amount) as total FROM source_data GROUP BY customer_id"
   }
   ```

2. **Configuration Resolution**:

   - Retrieves S3 bucket configuration from Airbyte destinations
   - Generates unique run ID (e.g., `sql-exec-a1b2c3d4`)
   - Determines source paths (Bronze layer or custom path)
   - Sets destination path in Silver layer

3. **SparkApplication Creation**:

   - Creates Kubernetes SparkApplication custom resource
   - Configures driver and executor pods
   - Sets up S3 credentials and environment
   - Embeds SQL transformation logic

4. **Job Execution**:

   - SparkOperator schedules driver pod
   - Driver spawns executor pods as needed
   - Executors read from S3 Bronze layer
   - Processes data using Spark SQL
   - Writes results to S3 Silver layer

5. **Monitoring & Status**:
   - Track job state (SUBMITTED, RUNNING, COMPLETED, FAILED)
   - View driver and executor logs
   - Monitor resource usage and metrics
   - Access Kubernetes events

### API Endpoints

#### 1. Submit Transformation

```http
POST /spark/transform
```

**Request Body:**

```json
{
  "sql": "SELECT * FROM parquet.`source_data` WHERE date >= '2024-01-01'",
  "source_path": "s3://bucket/bronze/data", // Optional
  "write_mode": "overwrite", // append | overwrite
  "executor_instances": 2,
  "executor_cores": 2,
  "executor_memory": "2g",
  "driver_cores": 1,
  "driver_memory": "1g"
}
```

**Response:**

```json
{
  "run_id": "a1b2c3d4",
  "spark_application": "sql-exec-a1b2c3d4",
  "status": "submitted",
  "source": "s3a://bucket/bronze/data",
  "destination": "s3a://bucket/silver/a1b2c3d4/",
  "sql": "SELECT * FROM ...",
  "namespace": "spark-operator",
  "message": "Transformation submitted..."
}
```

#### 2. Get Job Status

```http
GET  /spark/transform/{run_id}/status
```

**Response:**

```json
{
  "run_id": "a1b2c3d4",
  "spark_application": "sql-exec-a1b2c3d4",
  "namespace": "spark-operator",
  "state": "COMPLETED",
  "error_message": null,
  "driver_pod": "sql-exec-a1b2c3d4-driver",
  "executor_count": 2,
  "creation_time": "2024-10-07T10:30:00Z",
  "spark_version": "3.5.0",
  "image": "spark-custom:latest"
}
```

#### 3. Get Job Logs

```http
GET  /spark/transform/{run_id}/logs
```

Returns driver pod logs for debugging and monitoring.

#### 4. Get Job Events

```http
GET  /spark/transform/{run_id}/events
```

Returns Kubernetes events related to the Spark job.

#### 5. Get Job Metrics

```http
GET  /spark/transform/{run_id}/metrics
```

Returns resource usage metrics (CPU, memory, execution time).

#### 6. List Jobs

```http
GET  /spark/transform/jobs?limit=20&status_filter=RUNNING
```

Lists recent transformation jobs with filtering options.

### Features

✅ **Distributed Processing**: Leverage Spark's distributed computing for large datasets  
✅ **Kubernetes-Native**: Runs as native Kubernetes workloads with auto-scaling  
✅ **S3 Integration**: Direct read/write from S3-compatible storage  
✅ **Flexible Resources**: Configure driver and executor resources per job  
✅ **Multiple Write Modes**: Support for append and overwrite modes  
✅ **Comprehensive Monitoring**: Logs, events, metrics, and status tracking  
✅ **Fault Tolerance**: Automatic retries and pod rescheduling

### Resource Configuration

| Parameter            | Default | Description               |
| -------------------- | ------- | ------------------------- |
| `executor_instances` | 1       | Number of Spark executors |
| `executor_cores`     | 1       | CPU cores per executor    |
| `executor_memory`    | 512m    | Memory per executor       |
| `driver_cores`       | 1       | CPU cores for driver      |
| `driver_memory`      | 512m    | Memory for driver         |

### Example Use Cases

**1. Bronze to Silver - Clean Customer Data**

```json
{
  "sql": "SELECT DISTINCT customer_id, name, email, created_at FROM parquet.`customer_raw` WHERE email IS NOT NULL"
}
```

**2. Join Multiple Sources**

```json
{
  "sql": "SELECT o.order_id, o.amount, c.customer_name FROM parquet.`orders` o JOIN parquet.`customers` c ON o.customer_id = c.id"
}
```

**3. Aggregate Sales Data**

```json
{
  "sql": "SELECT date, product_id, SUM(quantity) as total_qty, SUM(revenue) as total_revenue FROM parquet.`sales` GROUP BY date, product_id",
  "executor_instances": 3,
  "executor_memory": "4g"
}
```

---

## DBT Transformation API

### Purpose

The DBT Transformation API provides SQL-driven data transformations using dbt (data build tool), designed for:

- **Business logic transformations** from Silver to Gold layer
- **Analytics-ready data models** for BI tools
- **Incremental updates** to minimize processing time
- **Data quality and governance** with built-in testing
- **Version-controlled transformations** as code

### How It Works

#### Architecture Flow

```
Silver Layer → DBT + Trino → Gold Layer (Iceberg Tables)
     ↓             ↓                ↓
  Iceberg      SQL Engine      Business-Ready Data
  Tables    (Distributed Query)   (Analytics)
```

#### Key Components

1. **DBTTransformationService**: Manages dbt model lifecycle
2. **Trino**: Distributed SQL query engine for Iceberg tables
3. **Iceberg**: Table format for large analytic datasets
4. **Nessie**: Git-like catalog for data versioning
5. **dbt Core**: Transforms data using SQL and Jinja templates

#### Process Flow

1. **API Request**: Client submits SQL transformation with metadata

   ```json
   POST  /dbt/transform
   {
     "name": "customer_metrics",
     "sql_query": "SELECT customer_id, COUNT(*) as order_count FROM silver.orders GROUP BY customer_id",
     "materialization": "table"
   }
   ```

2. **Validation**:

   - Validates transformation name (alphanumeric + underscores)
   - Checks SQL for dangerous keywords (DROP, DELETE, etc.)
   - Ensures query contains SELECT statements
   - Validates materialization options

3. **Schema Verification**:

   - Connects to Trino
   - Ensures Silver and Gold schemas exist
   - Creates schemas if missing

4. **DBT Model Generation**:

   - Generates dbt model file with config block
   - Includes materialization strategy
   - Adds metadata (tags, owner, description)
   - Applies incremental settings if specified

   ```sql
   {{ config(
       materialized='table',
       tags=['api_generated', 'customer']
   ) }}

   SELECT customer_id, COUNT(*) as order_count
   FROM silver.orders
   GROUP BY customer_id
   ```

5. **DBT Execution**:

   - Creates temporary model file
   - Executes `dbt run --select model_name`
   - Monitors execution progress
   - Captures execution logs

6. **Table Creation**:

   - dbt connects to Trino
   - Trino executes SQL on Iceberg tables
   - Creates/updates Gold layer table
   - Applies partitioning and optimization

7. **Post-Processing**:

   - Queries table statistics (row count, size)
   - Records execution time
   - Updates transformation metadata
   - Cleans up temporary files

8. **Response**:
   - Returns transformation ID
   - Includes Gold table name
   - Reports row count and metrics
   - Provides execution status

### API Endpoints

#### 1. Create Transformation

```http
POST  /dbt/transform
```

**Request Body:**

```json
{
  "name": "customer_revenue_summary",
  "sql_query": "SELECT customer_id, SUM(amount) as total_revenue, COUNT(*) as order_count FROM silver.transactions WHERE date >= '2024-01-01' GROUP BY customer_id",
  "description": "Aggregates customer revenue and order metrics",
  "materialization": "table",
  "tags": ["revenue", "customer", "daily"],
  "owner": "data-team",
  "incremental_strategy": null,
  "unique_key": null
}
```

**Response:**

```json
{
  "transformation_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "customer_revenue_summary",
  "status": "completed",
  "gold_table_name": "gold.customer_revenue_summary",
  "row_count": 15420,
  "execution_time_seconds": 12.5,
  "created_at": "2024-10-07T10:30:00Z",
  "updated_at": "2024-10-07T10:30:12Z"
}
```

#### 2. List Transformations

```http
GET  /dbt/transformations?page=1&page_size=20&status=completed
```

**Response:**

```json
{
  "transformations": [
    {
      "transformation_id": "...",
      "name": "customer_revenue_summary",
      "status": "completed",
      "created_at": "2024-10-07T10:30:00Z"
    }
  ],
  "total_count": 45,
  "page": 1,
  "page_size": 20
}
```

#### 3. Get Transformation Details

```http
GET  /dbt/transformations/{transformation_id}
```

Returns complete transformation metadata, SQL query, and execution details.

#### 4. List Silver Layer Sources

```http
GET  /dbt/sources/silver
```

Lists available tables in the Silver layer for transformation.

#### 5. List Gold Layer Tables

```http
GET  /dbt/tables/gold
```

Lists all Gold layer tables created by transformations.
 
 
### Features

✅ **SQL-Driven**: Pure SQL transformations without coding  
✅ **Multiple Materializations**: Tables, views, and incremental models  
✅ **Incremental Processing**: Process only new/changed data  
✅ **Built-in Security**: SQL injection protection and query validation  
✅ **Metadata Management**: Track transformations with descriptions, tags, and owners  
✅ **Iceberg Integration**: ACID transactions and time-travel capabilities  
✅ **Trino-Powered**: Distributed query execution for performance  
✅ **API-Triggered**: On-demand execution, no scheduled jobs

### Materialization Types

| Type            | Use Case                                     | Performance  | Storage           |
| --------------- | -------------------------------------------- | ------------ | ----------------- |
| **Table**       | Small to medium datasets, frequently queried | Fast reads   | Higher storage    |
| **View**        | Always-fresh data, infrequently queried      | Slower reads | No storage        |
| **Incremental** | Large datasets, append-only or merge updates | Fast updates | Optimized storage |

### Incremental Strategies

| Strategy          | Description                          | When to Use                  |
| ----------------- | ------------------------------------ | ---------------------------- |
| **append**        | Add new rows only                    | Event logs, time-series data |
| **merge**         | Update existing, insert new (upsert) | Slowly changing dimensions   |
| **delete_insert** | Delete matching rows, insert new     | Full partition refresh       |

### Example Use Cases

**1. Customer Lifetime Value**

```json
{
  "name": "customer_ltv",
  "sql_query": "SELECT customer_id, SUM(revenue) as lifetime_value, COUNT(DISTINCT order_id) as total_orders, AVG(revenue) as avg_order_value FROM silver.orders GROUP BY customer_id",
  "materialization": "table",
  "tags": ["metrics", "customer"],
  "description": "Calculate customer lifetime value metrics"
}
```

**2. Daily Revenue Report (View)**

```json
{
  "name": "daily_revenue_view",
  "sql_query": "SELECT DATE(order_date) as date, SUM(amount) as revenue, COUNT(*) as order_count FROM silver.orders GROUP BY DATE(order_date)",
  "materialization": "view",
  "description": "Real-time daily revenue view"
}
```

**3. Incremental Product Inventory**

```json
{
  "name": "product_inventory",
  "sql_query": "SELECT product_id, warehouse_id, quantity, updated_at FROM silver.inventory_changes",
  "materialization": "incremental",
  "incremental_strategy": "merge",
  "unique_key": ["product_id", "warehouse_id"],
  "description": "Track product inventory with incremental updates"
}
```

**4. Customer Segmentation**

```json
{
  "name": "customer_segments",
  "sql_query": "SELECT customer_id, CASE WHEN total_revenue > 10000 THEN 'VIP' WHEN total_revenue > 1000 THEN 'REGULAR' ELSE 'NEW' END as segment FROM (SELECT customer_id, SUM(amount) as total_revenue FROM silver.transactions GROUP BY customer_id)",
  "materialization": "table",
  "tags": ["segmentation", "marketing"]
}
```
  
## Architecture

### Data Lake Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
│  PostgreSQL │ MySQL │ MongoDB │ APIs │ Files │ Kafka       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
           ┌─────────────────────┐
           │   AIRBYTE INGESTION │
           └──────────┬───────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   BRONZE LAYER (Raw Data)                    │
│              S3: s3://bucket/bronze/                        │
│         Format: Parquet, JSON, CSV (as ingested)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │  SPARK TRANSFORMATION API │
         │  /api/v1/spark/transform  │
         │  - Clean data             │
         │  - Standardize formats    │
         │  - Remove duplicates      │
         │  - Join sources           │
         └──────────┬────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                SILVER LAYER (Processed Data)                 │
│              S3: s3://bucket/silver/                        │
│         Format: Parquet (Iceberg Tables)                    │
│         Quality: Validated, Standardized                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │   DBT TRANSFORMATION API  │
         │  /api/v1/dbt/transform    │
         │  - Business logic         │
         │  - Aggregations           │
         │  - Metrics calculation    │
         │  - Dimensional modeling   │
         └──────────┬────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│               GOLD LAYER (Analytics-Ready Data)              │
│              S3: s3://bucket/gold/                          │
│         Format: Iceberg Tables (ACID compliant)            │
│         Usage: BI Tools, ML Models, Analytics              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ┌────────────────────────┐
         │   DATA CONSUMPTION     │
         │  - Tableau / PowerBI   │
         │  - Jupyter Notebooks   │
         │  - ML Pipelines        │
         │  - REST APIs           │
         └────────────────────────┘
```
 
**Stack:**

- FastAPI (REST API)
- Kubernetes (Orchestration)
- SparkOperator (CRD Controller)
- Apache Spark 3.5.0 (Processing)
- S3/MinIO (Storage)
- Parquet (File Format)

#### DBT Transformation API

```
FastAPI → DBTTransformationService → dbt Core → Trino → Iceberg/Nessie
                                                           │
                                                           ▼
                                                      S3 Storage
```

**Stack:**

- FastAPI (REST API)
- dbt Core (Transformation)
- Trino (Query Engine)
- Iceberg (Table Format)
- Nessie (Catalog)
- S3/MinIO (Storage)

---

## Best Practices

### Spark Transformation API

#### 1. **Resource Optimization**

```json
// For small datasets (< 1GB)
{
  "executor_instances": 1,
  "executor_cores": 1,
  "executor_memory": "512m"
}

// For medium datasets (1-10GB)
{
  "executor_instances": 2,
  "executor_cores": 2,
  "executor_memory": "2g"
}

// For large datasets (> 10GB)
{
  "executor_instances": 5,
  "executor_cores": 4,
  "executor_memory": "4g"
}
```

#### 2. **SQL Best Practices**

- Use column pruning: `SELECT col1, col2` instead of `SELECT *`
- Apply filters early: `WHERE date >= '2024-01-01'`
- Avoid complex nested queries; break into steps
- Use partition columns for filtering when available

#### 3. **Error Handling**

- Monitor job status with `/transform/{run_id}/status`
- Check logs if job fails: `/transform/{run_id}/logs`
- Review Kubernetes events: `/transform/{run_id}/events`

#### 4. **Performance Tips**

- Partition large datasets by date or category
- Use `write_mode: "append"` for incremental loads
- Coalesce output files for better read performance
- Cache intermediate results for complex pipelines

### DBT Transformation API

#### 1. **Materialization Selection**

```
Use TABLE when:
  ✓ Query is slow (> 5 seconds)
  ✓ Data accessed frequently
  ✓ Dataset is relatively small (< 1TB)

Use VIEW when:
  ✓ Always need fresh data
  ✓ Data changes frequently
  ✓ Simple transformations

Use INCREMENTAL when:
  ✓ Dataset is large (> 100GB)
  ✓ Only new data needs processing
  ✓ Data has temporal/unique keys
```

#### 2. **SQL Quality**

- Write clean, readable SQL with proper formatting
- Use meaningful column aliases
- Add comments for complex logic
- Avoid SELECT \*; be explicit about columns

#### 3. **Metadata Management**

```json
{
  "name": "descriptive_snake_case_name",
  "description": "Clear explanation of what the transformation does",
  "tags": ["domain", "frequency", "owner"],
  "owner": "team-name"
}
```

#### 4. **Incremental Strategy**

```json
// For event/log data (append only)
{
  "materialization": "incremental",
  "incremental_strategy": "append"
}

// For dimension tables (updates + inserts)
{
  "materialization": "incremental",
  "incremental_strategy": "merge",
  "unique_key": ["id"]
}

// For full partition refresh
{
  "materialization": "incremental",
  "incremental_strategy": "delete_insert",
  "unique_key": ["date", "id"]
}
```

#### 5. **Performance Optimization**

- Use incremental models for large tables
- Partition Gold tables by date when possible
- Limit data scanned with WHERE clauses
- Create views for simple transformations
- Monitor execution time and optimize slow queries

### General Best Practices

#### 1. **Naming Conventions**

```
Bronze Layer:   raw_source_tablename
Silver Layer:   cleaned_source_tablename
Gold Layer:     business_concept_name

Examples:
Bronze:  raw_postgres_orders
Silver:  cleaned_orders
Gold:    customer_lifetime_value
```

#### 2. **Data Quality**

- Validate data in Silver layer before creating Gold tables
- Use dbt tests for data quality checks (future feature)
- Document data lineage and transformations
- Monitor transformation success rates

#### 3. **Security**

- Never include credentials in SQL queries
- Use environment variables for sensitive config
- Validate and sanitize SQL inputs
- Apply least-privilege access to S3 buckets

#### 4. **Monitoring**

- Track transformation execution times
- Set up alerts for failed jobs
- Monitor resource usage and costs
- Review logs regularly for issues

#### 5. **Documentation**

- Document each transformation's purpose
- Maintain data dictionaries
- Update examples when business logic changes
- Version control transformation definitions

 

---

## API Reference Summary

### Spark Transformation API Endpoints

| Method | Endpoint                                   | Description               |
| ------ | ------------------------------------------ | ------------------------- |
| POST   | `/spark/transform`                  | Submit transformation job |
| GET    | `/spark/transform/{run_id}/status`  | Get job status            |
| GET    | `/spark/transform/{run_id}/logs`    | Get job logs              |
| GET    | `/spark/transform/{run_id}/events`  | Get Kubernetes events     |
| GET    | `/spark/transform/{run_id}/metrics` | Get job metrics           |
| GET    | `/spark/transform/jobs`             | List all jobs             |

### DBT Transformation API Endpoints

| Method | Endpoint                           | Description                |
| ------ | ---------------------------------- | -------------------------- |
| POST   | `/dbt/transform`            | Create transformation      |
| GET    | `/dbt/transformations`      | List transformations       |
| GET    | `/dbt/transformations/{id}` | Get transformation details |
| DELETE | `/dbt/transformations/{id}` | Delete transformation      |
| GET    | `/dbt/sources/silver`       | List Silver layer tables   |
| GET    | `/dbt/tables/gold`          | List Gold layer tables     |
---

 
