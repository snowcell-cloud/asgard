# Asgard Platform - Complete Architecture & Visual Guide

**Unified Technical Architecture, Diagrams & System Design**  
**Last Updated:** November 24, 2025  
**Version:** 2.0

---

## 📋 Table of Contents

1. [Platform Overview](#platform-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagrams](#architecture-diagrams)
4. [Component Design](#component-design)
5. [Data Flow Architecture](#data-flow-architecture)
6. [Iceberg Integration](#iceberg-integration)
7. [Feast Feature Store](#feast-feature-store)
8. [MLflow Integration](#mlflow-integration)
9. [Sequence Diagrams](#sequence-diagrams)
10. [Network & Storage Architecture](#network--storage-architecture)
11. [Security & Performance](#security--performance)

---

## Platform Overview

### High-Level System Design

Asgard is a **unified data lakehouse platform** built on Kubernetes that orchestrates the complete data lifecycle from ingestion to ML deployment through a single FastAPI gateway.

```mermaid
graph TB
    subgraph External["External Systems"]
        API1[REST APIs]
    end

    subgraph Platform["Asgard Platform - Kubernetes Cluster"]
        subgraph APILayer["API Layer"]
            Gateway["FastAPI Gateway<br/>Port 80"]
        end

        subgraph Processing["Processing Components"]
            Airbyte["Airbyte<br/>Data Ingestion"]
                        Spark["Spark on K8s<br/>Data Processing"]
                        DBT["DBT + Trino<br/>SQL Transformations"]
                        Feast["Feast<br/>Feature Store"]
                        MLflow["MLflow<br/>ML Platform"]
        end

        subgraph Lakehouse["Data Lakehouse"]
            Bronze["Bronze Layer<br/>Raw Data"]
            Silver["Silver Layer<br/>Cleaned Data"]
            Gold["Gold Layer<br/>Aggregated Metrics"]
        end

        subgraph StorageMeta["Storage & Metadata"]
            S3["S3 Object Storage<br/>Iceberg + Parquet"]
            Postgres["PostgreSQL<br/>Metadata"]
            Nessie["Nessie Catalog<br/>Data Versioning"]
        end
    end

    
    API1 --> Gateway
    Gateway --> Airbyte
    Gateway --> Spark
    Gateway --> DBT
    Gateway --> Feast
    Gateway --> MLflow

    Airbyte --> Bronze
    Spark --> Silver
    DBT --> Gold

    Bronze --> S3
    Silver --> S3
    Gold --> S3
    S3 <--> Nessie

    Feast -.Direct Read.-> Gold
    MLflow --> Postgres
    Feast --> Postgres

    classDef api fill:#e1f5ff,stroke:#01579b,color:#000
    classDef process fill:#f3e5f5,stroke:#4a148c,color:#000
    classDef data fill:#e8f5e9,stroke:#1b5e20,color:#000
    classDef storage fill:#fff3e0,stroke:#e65100,color:#000

    class Gateway api
    class Airbyte,Spark,DBT,Feast,MLflow process
    class Bronze,Silver,Gold data
    class S3,Postgres,Nessie storage
```

### Key Architectural Principles

1. **API-First Design** - All operations accessible via REST API
2. **Medallion Architecture** - Bronze → Silver → Gold data layers
3. **Zero Data Duplication** - Feast reads directly from Iceberg S3 Parquet
4. **Kubernetes Native** - Cloud-agnostic, scalable deployment
5. **Separation of Concerns** - Each component has a single responsibility
6. **Event-Driven** - Asynchronous job execution with status tracking

---

## Technology Stack

### Core Components

| Layer               | Component      | Version     | Purpose                        |
| ------------------- | -------------- | ----------- | ------------------------------ |
| **API Gateway**     | FastAPI        | 0.104+      | REST API server                |
| **Data Ingestion**  | Airbyte        | OSS         | CDC and data connectors        |
| **Data Processing** | Apache Spark   | 3.5.0       | Distributed data processing    |
| **SQL Transform**   | DBT + Trino    | 1.6+ / 428+ | SQL-based transformations      |
| **Feature Store**   | Feast          | 0.35+       | Feature management             |
| **ML Platform**     | MLflow         | 2.16.2      | Experiment tracking & registry |
| **Data Lakehouse**  | Apache Iceberg | 1.5+        | Table format                   |
| **Data Catalog**    | Project Nessie | 0.74+       | Version control for data       |
| **Object Storage**  | AWS S3         | -           | Data and artifact storage      |
| **Metadata DB**     | PostgreSQL     | 13+         | MLflow backend, Feast registry |
| **Orchestration**   | Kubernetes     | 1.27+       | Container orchestration        |
| **Spark Operator**  | Spark on K8s   | 3.5.0       | Spark job management           |

### Language |

| Technology  | Version | Usage                               |
| ----------- | ------- | ----------------------------------- |
| **Python**  | 3.11    | Primary language for all services   |
| **PySpark** | 3.5.0   | Spark transformations               |
| **SQL**     | -       | DBT models, Trino queries           |
| **YAML**    | -       | Configuration, Kubernetes manifests |
| **Parquet** | -       | Data storage format                 |

---

## Architecture Diagrams

### Complete System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        User["Data Engineer / ML Engineer"]
        API_Docs["Swagger UI<br/>localhost:8000/docs"]
    end

    subgraph API["API Layer - FastAPI Gateway"]
        Router_Airbyte["datasource / datasink / ingestion"]
        Router_Spark["spark transform"]
        Router_DBT["dbt transform"]
        Router_Feast["feast features / status"]
        Router_MLOps["mlops training / inference"]
    end

    subgraph Platform["Platform Components"]
        direction TB

        subgraph Airbyte_System["Airbyte Platform"]
            Airbyte_Server[Airbyte Server]
            Airbyte_Worker[Workers]
            Airbyte_Temporal[Temporal]
        end

        subgraph Spark_System["Spark on Kubernetes"]
            Spark_Operator[Spark Operator]
            Spark_Driver[Driver Pod]
            Spark_Executors[Executor Pods]
        end

        subgraph DBT_System["DBT + Trino"]
            DBT_Service[DBT Service]
            Trino_Coordinator[Trino Coordinator]
            Trino_Workers[Trino Workers]
        end

        subgraph Feast_System["Feast Feature Store"]
            Feast_Registry["Feature Registry<br/>PostgreSQL"]
            Feast_OfflineStore["Offline Store<br/>File-based"]
        end

        subgraph MLflow_System["MLflow Platform"]
            MLflow_Tracking[Tracking Server]
            MLflow_Registry[Model Registry]
            MLflow_Inference[Inference Service]
        end
    end

    subgraph Lakehouse["Data Lakehouse - Medallion Architecture"]
        direction LR
        Bronze["Bronze Layer<br/>Raw Data<br/>Parquet"]
        Silver["Silver Layer<br/>Cleaned Data<br/>Parquet"]
        Gold["Gold Layer<br/>ML-Ready Features<br/>Parquet"]

        Bronze -->|"Spark SQL\nCleansing"| Silver
        Silver -->|"DBT + Trino\nAggregation"| Gold
    end

    subgraph Storage["Storage and Catalog"]
        S3["S3 Object Storage<br/>s3://airbytedestination1"]
        Nessie["Nessie Catalog<br/>Git-like Versioning"]
        Postgres["PostgreSQL<br/>Metadata Store"]
    end

    User --> API_Docs
    API_Docs --> Router_Airbyte
    API_Docs --> Router_Spark
    API_Docs --> Router_DBT
    API_Docs --> Router_Feast
    API_Docs --> Router_MLOps

    Router_Airbyte --> Airbyte_Server
    Router_Spark --> Spark_Operator
    Router_DBT --> DBT_Service
    Router_Feast --> Feast_Registry
    Router_MLOps --> MLflow_Tracking

    Airbyte_Server --> Airbyte_Worker
    Airbyte_Server --> Airbyte_Temporal
    Spark_Operator --> Spark_Driver --> Spark_Executors
    DBT_Service --> Trino_Coordinator --> Trino_Workers

    Airbyte_Worker -->|"Write"| Bronze
    Spark_Executors -->|"Read/Write"| Bronze
    Spark_Executors -->|"Read/Write"| Silver
    Trino_Workers -->|"Read/Write"| Silver
    Trino_Workers -->|"Read/Write"| Gold

    Bronze --> S3
    Silver --> S3
    Gold --> S3
    S3 <-->|"Metadata"| Nessie

    Feast_OfflineStore -."Direct S3 Read<br/>NO COPY!".-> Gold
    Feast_Registry --> Postgres
    MLflow_Tracking --> Postgres
    MLflow_Tracking -->|"Artifacts"| S3

    classDef clientStyle fill:#e3f2fd,stroke:#1976d2,color:#000,stroke-width:2px
    classDef apiStyle fill:#fff3e0,stroke:#f57c00,color:#000,stroke-width:2px
    classDef processStyle fill:#f3e5f5,stroke:#7b1fa2,color:#000,stroke-width:2px
    classDef dataStyle fill:#e8f5e9,stroke:#388e3c,color:#000,stroke-width:2px
    classDef storageStyle fill:#fce4ec,stroke:#c2185b,color:#000,stroke-width:2px

    class User,API_Docs clientStyle
    class Router_Airbyte,Router_Spark,Router_DBT,Router_Feast,Router_MLOps apiStyle
    class Airbyte_System,Spark_System,DBT_System,Feast_System,MLflow_System processStyle
    class Bronze,Silver,Gold dataStyle
    class S3,Nessie,Postgres storageStyle
```

### Data Flow - End-to-End Pipeline

```mermaid
flowchart LR
    subgraph Sources["External Sources"]
        PG[(PostgreSQL)]
        MySQL[(MySQL)]
        APIs[REST APIs]
    end

    subgraph Phase1["Phase 1: Ingestion"]
        Airbyte_Sync["Airbyte Sync Job"]
        Bronze_Store["Bronze Layer\n100K rows\nRaw as-is"]
    end

    subgraph Phase2["Phase 2: Cleansing"]
        Spark_Clean["Spark SQL\n- Deduplication\n- Type Casting\n- Null Handling"]
        Silver_Store["Silver Layer\n98.5K rows\nCleaned"]
    end

    subgraph Phase3["Phase 3: Aggregation"]
        DBT_Agg["DBT + Trino\n- Joins\n- Aggregations\n- Feature Engineering"]
        Gold_Store["Gold Layer\nML-Ready Features"]
    end

    subgraph Phase4["Phase 4: Feature Store"]
        Feast_Register["Feast Registration\nDirect S3 Path"]
        Feature_Views["Feature Views\nTime-Travel Queries"]
    end

    subgraph Phase5["Phase 5: ML Training"]
        MLflow_Train["MLflow Training\n- Fetch Features\n- Train Model\n- Log Metrics"]
        Model_Registry["Model Registry\nVersioned Models"]
    end

    subgraph Phase6["Phase 6: Inference"]
        Inference_API["Inference Service\nPredictions"]
        Applications["ML Applications"]
    end    PG --> Airbyte_Sync
    MySQL --> Airbyte_Sync
    APIs --> Airbyte_Sync
    Airbyte_Sync -->|"Write Parquet"| Bronze_Store
    Bronze_Store --> Spark_Clean
    Spark_Clean -->|"Write Parquet"| Silver_Store
    Silver_Store --> DBT_Agg
    DBT_Agg -->|"Write Parquet"| Gold_Store
    Gold_Store -."Direct Read".-> Feast_Register
    Feast_Register --> Feature_Views
    Feature_Views --> MLflow_Train
    MLflow_Train --> Model_Registry
    Model_Registry --> Inference_API
    Inference_API --> Applications

    classDef sourceStyle fill:#e1f5fe,stroke:#01579b,color:#000
    classDef transformStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef dataStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef mlStyle fill:#fff3e0,stroke:#ef6c00,color:#000

    class PG,MySQL,APIs sourceStyle
    class Airbyte_Sync,Spark_Clean,DBT_Agg transformStyle
    class Bronze_Store,Silver_Store,Gold_Store,Feature_Views dataStyle
    class Feast_Register,MLflow_Train,Model_Registry,Inference_API,Applications mlStyle
```

---

## Component Design

### 1. FastAPI Gateway

**Purpose**: Unified REST API for all platform operations

**Architecture**:

```

app/
├── __init__.py
├── main.py               # FastAPI application
├── config.py             # Configuration management
│
├── airbyte/              # Airbyte integration
│   ├── router.py         # API endpoints
│   ├── schemas.py        # Pydantic models
│   └── client.py         # Airbyte API client
│
├── data_transformation/  # Spark integration
│   ├── router.py
│   ├── schemas.py
│   ├── client.py         # Spark Operator client
│   └── service.py        # Business logic
│
├── dbt_transformations/  # DBT integration
│   ├── router.py
│   ├── schemas.py
│   └── service.py        # DBT + Trino orchestration
│
├── feast/                # Feast integration
│   ├── router.py
│   ├── schemas.py
│   └── service.py        # Feature store operations
│
├── mlops/                # MLOps integration
│   ├── router.py
│   ├── schemas.py
│   ├── service.py        # Training orchestration
│   └── deployment_service.py  # Inference serving
│
└── data_products/        # Direct data access
    ├── router.py
    ├── schemas.py
    └── client.py         # Trino client
```

**Key Features**:

- **OpenAPI/Swagger** - Auto-generated API documentation
- **Pydantic Validation** - Type-safe request/response models
- **Async Support** - Non-blocking I/O for better performance
- **Dependency Injection** - Clean separation of concerns
- **Error Handling** - Standardized error responses

### 2. Airbyte Platform

**Purpose**: Data ingestion from external sources to Bronze layer

```mermaid
flowchart TB
    subgraph External["External Data Sources"]
        Source1["PostgreSQL\ncustomers table"]
        Source2["MySQL\ntransactions table"]
        Source3["REST API\nsupport tickets"]
    end

    subgraph Airbyte["Airbyte Platform"]
        Server["Airbyte Server\n:8001"]
        Temporal["Temporal\nWorkflow Engine"]
        Worker1["Worker Pod 1"]
        Worker2["Worker Pod 2"]
        Database["PostgreSQL\nAirbyte Config"]
    end

    subgraph Bronze["Bronze Layer"]
        Table1["iceberg.bronze.customers\nParquet"]
        Table2["iceberg.bronze.transactions\nParquet"]
        Table3["iceberg.bronze.support_tickets\nParquet"]
    end

    Source1 --> Worker1
    Source2 --> Worker1
    Source3 --> Worker2

    Server --> Temporal
    Temporal --> Worker1
    Temporal --> Worker2
    Server <--> Database

    Worker1 --> Table1
    Worker1 --> Table2
    Worker2 --> Table3

    classDef sourceStyle fill:#e3f2fd,stroke:#1565c0,color:#000
    classDef airbyteStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef dataStyle fill:#e8f5e9,stroke:#2e7d32,color:#000

    class Source1,Source2,Source3 sourceStyle
    class Server,Temporal,Worker1,Worker2,Database airbyteStyle
    class Table1,Table2,Table3 dataStyle
```

**Data Flow**:

```

Source DB → Airbyte Connector → Normalization → S3/Iceberg (Bronze)
```

**Supported Sources**:

- PostgreSQL
- MySQL

### 3. Spark on Kubernetes

**Purpose**: Distributed data processing (Bronze → Silver)

```mermaid
flowchart TB
    subgraph API["API Request"]
        Request["POST /spark/transform<br/> job_name, sql_query, output_table"]
    end

    subgraph Operator["Spark Operator"]
        CustomResource["SparkApplication<br/>Custom Resource"]
        Controller["Operator Controller"]
    end

    subgraph SparkCluster["Spark Cluster"]
        Driver["Driver Pod<br/>- Job Coordinator<br/>- Spark SQL<br/>- UI :4040"]

        subgraph Executors["Executor Pods"]
            Exec1["Executor 1<br/>2 cores, 4GB"]
            Exec2["Executor 2<br/>2 cores, 4GB"]
            Exec3["Executor 3<br/>2 cores, 4GB"]
        end
    end

    subgraph Data["Data Lakehouse"]
        Bronze["Bronze Layer<br/>Read"]
        Silver["Silver Layer<br/>Write"]
    end

    Request --> CustomResource
    CustomResource --> Controller
    Controller -->|"Create"| Driver
    Driver -->|"Request Executors"| Controller
    Controller -->|"Create"| Exec1
    Controller -->|"Create"| Exec2
    Controller -->|"Create"| Exec3

    Driver <-->|"Tasks"| Exec1
    Driver <-->|"Tasks"| Exec2
    Driver <-->|"Tasks"| Exec3
    Exec1 -->|"Read"| Bronze
    Exec2 -->|"Read"| Bronze
    Exec3 -->|"Read"| Bronze
    Exec1 -->|"Write"| Silver
    Exec2 -->|"Write"| Silver
    Exec3 -->|"Write"| Silver

    classDef apiStyle fill:#fff3e0,stroke:#f57c00,color:#000
    classDef operatorStyle fill:#e1f5fe,stroke:#0277bd,color:#000
    classDef sparkStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef dataStyle fill:#e8f5e9,stroke:#2e7d32,color:#000

    class Request apiStyle
    class CustomResource,Controller operatorStyle
    class Driver,Exec1,Exec2,Exec3 sparkStyle
    class Bronze,Silver dataStyle
```

#### Spark Documentation

**Key Capabilities**:

- **SQL-based transformations** via Spark SQL
- **Iceberg integration** for reading/writing tables
- **Dynamic resource allocation**
- **Auto-scaling** executors based on workload
- **Job monitoring** via Spark UI

**Docker Image Configuration**:

Base Image: `apache/spark-py:v3.4.0`

**Included Dependencies**:

- Hadoop AWS 3.3.4 (S3A support)
- AWS Java SDK 1.12.262
- Iceberg Spark Runtime 1.9.0
- Iceberg Nessie 1.9.0
- Nessie Client 0.104.1

**SQL Transformation Script** (`sql_transform_embedded.py`):

Core features:

1. Generic SQL transformations via Spark SQL
2. Multi-source Parquet reading
3. Automatic Iceberg table creation in Nessie catalog
4. S3A filesystem auto-configuration
5. Robust error handling with fallback strategies

Configuration:

```python
ICEBERG_ENABLED = True
ICEBERG_CATALOG_NAME = "nessie"
ICEBERG_WAREHOUSE = "s3a://airbytedestination1/iceberg/"
NESSIE_URI = "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
NESSIE_REF = "main"
ICEBERG_WRITE_MODE = "append"  # append | overwrite | create_or_replace
```

**Spark Configuration Parameters**:

- `spark.sql.transform.query` - SQL query to execute
- `spark.sql.transform.sources` - JSON array of source paths
- `spark.sql.transform.destination` - Destination path
- `spark.sql.transform.writeMode` - Write mode

**Resource Recommendations**:

| Workload | Executors | Cores | Memory | Driver Memory |
| -------- | --------- | ----- | ------ | ------------- |
| Small    | 1-2       | 1-2   | 2g     | 1g            |
| Medium   | 2-5       | 2     | 4g     | 2g            |
| Large    | 5-10      | 2-4   | 8g     | 4g            |
| XLarge   | 10-20     | 4     | 16g    | 8g            |

**CI/CD Pipeline**:

- Automated build on push to `dev` branch
- Pushed to ECR: `637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom`
- Automated testing of Spark, Python, S3A, and PySpark
- Security vulnerability scanning via ECR

### 4. DBT + Trino

**Purpose**: SQL-based business logic transformations (Silver → Gold)

```mermaid
flowchart LR
    subgraph API["API Layer"]
        Request["POST /dbt/transform\nmodel_name, dependencies"]
    end

    subgraph DBT["DBT Service"]
        Service["DBT Service"]
        Models["SQL Models<br/> - customer_metrics.sql<br/>- product_analytics.sql"]
    end

    subgraph Trino["Trino Cluster"]
        Coordinator["Trino Coordinator<br/>Query Planning"]
        Worker1["Worker 1<br/>Query Execution"]
        Worker2["Worker 2<br/>Query Execution"]
    end

    subgraph Iceberg["Iceberg Tables"]
        Silver["Silver Layer<br/>customers_cleaned<br/>transactions_cleaned"]
        Gold["Gold Layer<br/>customer_metrics<br/>product_analytics"]
    end

    subgraph Catalog["Nessie Catalog"]
        Nessie["Nessie Server\nTable Metadata\nVersion Control"]
    end

    Request --> Service
    Service --> Models
    Models -->|"Generate SQL"| Coordinator
    Coordinator --> Worker1
    Coordinator --> Worker2
    Worker1 -->|"Read"| Silver
    Worker2 -->|"Read"| Silver
    Worker1 -->|"Write"| Gold
    Worker2 -->|"Write"| Gold

    Silver <-->|"Metadata"| Nessie
    Gold <-->|"Metadata"| Nessie

    classDef apiStyle fill:#fff3e0,stroke:#f57c00,color:#000
    classDef dbtStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef trinoStyle fill:#e1f5fe,stroke:#0277bd,color:#000
    classDef dataStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef catalogStyle fill:#fce4ec,stroke:#c2185b,color:#000

    class Request apiStyle
    class Service,Models dbtStyle
    class Coordinator,Worker1,Worker2 trinoStyle
    class Silver,Gold dataStyle
    class Nessie catalogStyle
```

### 5. Feast Feature Store

**Purpose**: Feature management for ML workflows

```mermaid
flowchart TB
    subgraph API["API Layer"]
        Register["POST /feast/features\nRegister from Iceberg"]
        Retrieve["GET /feast/features\nHistorical Retrieval"]
    end

    subgraph Feast["Feast Feature Store"]
        Service["Feast Service"]
        Registry["Feature Registry\nPostgreSQL"]
        OfflineStore["Offline Store\nFile-based"]
    end

    subgraph Iceberg["Iceberg Gold Layer"]
        Gold["S3 Parquet Files\ns3://.../gold/*/data/*.parquet"]
        Metadata["Iceberg Metadata\nSchema, Snapshots"]
    end

    subgraph Trino["Trino"]
        TrinoQuery["Trino Query Engine\nExtract S3 Path"]
    end

    subgraph ML["ML Applications"]
        Training["Training Scripts"]
        Inference["Inference Services"]
    end

    Register --> Service
    Service -->|"Query for Path"| TrinoQuery
    TrinoQuery -->|"$path column"| Metadata
    Metadata -->|"S3 Parquet Path"| Service
    Service -->|"FileSource config"| Registry

    Retrieve --> Service
    Service --> OfflineStore
    OfflineStore -."Direct S3 Read\nNO COPY!".-> Gold

    OfflineStore -->|"Features"| Training
    OfflineStore -->|"Features"| Inference

    classDef apiStyle fill:#fff3e0,stroke:#f57c00,color:#000
    classDef feastStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef dataStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef trinoStyle fill:#e1f5fe,stroke:#0277bd,color:#000
    classDef mlStyle fill:#fce4ec,stroke:#c2185b,color:#000

    class Register,Retrieve apiStyle
    class Service,Registry,OfflineStore feastStyle
    class Gold,Metadata dataStyle
    class TrinoQuery trinoStyle
    class Training,Inference mlStyle
```

**Unique Design**: Direct S3 Parquet reads from Iceberg Gold layer

### 6. MLflow Platform

**Purpose**: ML experiment tracking, model registry, and serving

```mermaid
flowchart TB
    subgraph API["API Layer"]
        Upload["POST /mlops/training/upload<br/>Training Script"]
        Deploy["POST /mlops/inference<br/>Prediction Request"]
    end

    subgraph MLflow["MLflow Platform"]
        Tracking["Tracking Server<br/>:5000"]
        Registry["Model Registry"]

        subgraph Backend["Storage Backend"]
            MetaDB["PostgreSQL<br/>Runs, Metrics, Params"]
            ArtifactS3["S3<br/>Models, Plots, Logs"]
        end
    end

    subgraph Execution["Training Execution"]
        TrainingPod["Training Job Pod<br/>- Install deps<br/>- Fetch features<br/>- Train model"]
    end

    subgraph Inference["Model Serving"]
        InferencePod["Inference Service<br/>- Load model<br/>- Make predictions"]
    end

    Upload --> Tracking
    Tracking -->|"Create Job"| TrainingPod
    TrainingPod -->|"Log Metrics"| MetaDB
    TrainingPod -->|"Save Model"| ArtifactS3
    TrainingPod -->|"Register"| Registry

    Deploy --> InferencePod
    InferencePod -->|"Load Model"| ArtifactS3
    Registry -->|"Version Info"| InferencePod

    classDef apiStyle fill:#fff3e0,stroke:#f57c00,color:#000
    classDef mlflowStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef storageStyle fill:#e1f5fe,stroke:#0277bd,color:#000
    classDef execStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000

    class Upload,Deploy apiStyle
    class Tracking,Registry mlflowStyle
    class MetaDB,ArtifactS3 storageStyle
    class TrainingPod,InferencePod execStyle
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

```mermaid
flowchart LR
    subgraph Bronze["🥉 Bronze Layer - Raw Data"]
        direction TB
        B1[Source: Airbyte Ingestion]
        B2[Format: Parquet as-is]
        B3[Schema: Source schema]
        B4[Retention: Indefinite]
        B1 --> B2 --> B3 --> B4
    end

    subgraph Silver["🥈 Silver Layer - Cleaned Data"]
        direction TB
        S1[Source: Spark Transformations]
        S2[Format: Parquet Snappy]
        S3[Operations: Cleansing, Validation]
        S4[Schema: Standardized]
        S1 --> S2 --> S3 --> S4
    end

    subgraph Gold["🥇 Gold Layer - Business Metrics"]
        direction TB
        G1[Source: DBT Transformations]
        G2[Format: Parquet Snappy]
        G3[Operations: Joins, Aggregations]
        G4[Schema: ML-ready Features]
        G1 --> G2 --> G3 --> G4
    end

    Bronze -->|Spark SQL <br/>Cleansing| Silver
    Silver -->|DBT + Trino<br/>Aggregation| Gold

    classDef bronzeStyle fill:#fbe9e7,stroke:#d84315,color:#000
    classDef silverStyle fill:#e0f2f1,stroke:#00695c,color:#000
    classDef goldStyle fill:#fff8e1,stroke:#f57f17,color:#000

    class Bronze,B1,B2,B3,B4 bronzeStyle
    class Silver,S1,S2,S3,S4 silverStyle
    class Gold,G1,G2,G3,G4 goldStyle
```

### S3 Storage Structure

```

s3://airbytedestination1/iceberg/

├── bronze/                          # Raw data from sources
│   ├── customers/
│   │   ├── metadata/
│   │   │   ├── v1.metadata.json    # Iceberg table metadata
│   │   │   ├── v2.metadata.json
│   │   │   └── snap-{id}.avro      # Snapshot manifests
│   │   └── data/
│   │       ├── 00000-0-{uuid}.parquet
│   │       └── 00001-1-{uuid}.parquet
│   ├── transactions/
│   └── support_tickets/
│
├── silver/                          # Cleaned, validated data
│   ├── customers_cleaned/
│   │   ├── metadata/
│   │   └── data/
│   │       └── *.parquet
│   ├── transactions_cleaned/
│   └── support_tickets_cleaned/
│
└── gold/                            # ML-ready features
    ├── customer_metrics/
    │   ├── metadata/
    │   └── data/
    │       └── *.parquet           ← Feast reads directly from here!
    ├── product_analytics/
    └── churn_predictions/
```

---

## Iceberg Integration

### Iceberg + Nessie Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Applications"]
        Spark[Spark Jobs]
        Trino[Trino Queries]
        DBT[DBT Models]
    end

    subgraph Nessie["Nessie Catalog - Git-like Version Control"]
        direction LR
        Main[main branch]
        Dev[dev branch]
        Staging[staging branch]

        Main -.merge.-> Staging
        Staging -.merge.-> Dev
    end

    subgraph Metadata["Iceberg Table Metadata"]
        Meta1[v1.metadata.json\nSchema v1]
        Meta2[v2.metadata.json\nSchema v2]
        Snap1[snap-123.avro\nSnapshot 1]
        Snap2[snap-456.avro\nSnapshot 2]
    end

    subgraph Data["Data Files in S3"]
        File1[file1.parquet\n100MB]
        File2[file2.parquet\n95MB]
        File3[file3.parquet\n102MB]
    end

    Spark & Trino & DBT -->|Catalog API| Nessie
    Nessie -->|Points to| Metadata
    Metadata -->|Manifest List| Snap1 & Snap2
    Snap1 & Snap2 -->|References| File1 & File2 & File3

    classDef clientStyle fill:#e3f2fd,stroke:#1565c0,color:#000
    classDef nessieStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef metaStyle fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef dataStyle fill:#e8f5e9,stroke:#2e7d32,color:#000

    class Spark,Trino,DBT clientStyle
    class Nessie,Main,Dev,Staging nessieStyle
    class Metadata,Meta1,Meta2,Snap1,Snap2 metaStyle
    class Data,File1,File2,File3 dataStyle
```

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
```

---

## Feast Feature Store

### Zero-Duplication Architecture

```mermaid
flowchart TB
    subgraph Traditional["❌ Traditional Approach - Data Duplication"]
        I1[Iceberg Gold Layer<br/>S3 Parquet]
        E1[Export/ETL Job]
        L1[Local Parquet Copy]
        F1[Feast Feature Store]

        I1 -->|Copy Data| E1
        E1 -->|Write| L1
        L1 --> F1

        Problem1[❌ 2x Storage Cost<br/>❌ Sync Overhead<br/>❌ Consistency Issues]
    end

    subgraph Asgard["✅ Asgard Approach - Zero Duplication"]
        I2[Iceberg Gold Layer<br/>S3 Parquet]
        F2[Feast Feature Store<br/>FileSource]

        F2 -.Direct S3 Read<br/>NO COPY!.-> I2

        Benefits2[✅ Single Source of Truth<br/>✅ No Storage Duplication<br/>✅ Immediate Consistency]
    end

    classDef problemStyle fill:#ffebee,stroke:#c62828,color:#000
    classDef goodStyle fill:#e8f5e9,stroke:#2e7d32,color:#000

    class Traditional,I1,E1,L1,F1,Problem1 problemStyle
    class Asgard,I2,F2,Benefits2 goodStyle
```

### Feature Registration Flow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Feast as Feast Service
    participant Trino as Trino
    participant Iceberg as Iceberg Metadata
    participant S3 as S3 Parquet Files

    User->>API: POST /feast/features<br/>{table: "customer_metrics"}
    API->>Feast: create_feature_view()

    Note over Feast: 1. Validate Table
    Feast->>Trino: SELECT * FROM iceberg.gold.customer_metrics LIMIT 1
    Trino->>Iceberg: Get table metadata
    Iceberg-->>Trino: Table exists, schema returned
    Trino-->>Feast: Table valid ✓

    Note over Feast: 2. Get S3 Path
    Feast->>Trino: SELECT "$path" FROM table LIMIT 1
    Trino->>Iceberg: Get file locations
    Iceberg->>S3: Resolve Parquet paths
    S3-->>Iceberg: File paths
    Iceberg-->>Trino: s3://.../data/*.parquet
    Trino-->>Feast: S3 Parquet path

    Note over Feast: 3. Register Feature View
    Feast->>Feast: Create FileSource(path=s3://...)
    Feast->>Feast: Register FeatureView

    Feast-->>API: Feature view registered ✓
    API-->>User: {status: "success", features: [...]}
```

## MLflow Integration

### Training Workflow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant MLflow as MLflow Server
    participant Pod as Training Pod
    participant Feast as Feast
    participant S3 as S3 Storage
    participant Registry as Model Registry

    User->>API: POST /mlops/training/upload<br/>{script, requirements}
    API->>MLflow: Create training job
    MLflow->>Pod: Create training pod

    activate Pod
    Pod->>Pod: Install requirements
    Pod->>Feast: Fetch features
    Feast->>S3: Read Parquet files
    S3-->>Feast: Feature data
    Feast-->>Pod: Features DataFrame

    Pod->>Pod: Train model
    Pod->>MLflow: Log metrics (accuracy, loss)
    Pod->>S3: Save model artifact
    Pod->>Registry: Register model
    deactivate Pod

    MLflow-->>API: Job complete, run_id
    API-->>User: {run_id, status: "completed"}
```

### Model Versioning

```mermaid
flowchart TB
    subgraph Models["customer_churn_predictor"]
        direction TB

        subgraph V1["Version 1 - Development"]
            V1_Metrics[Accuracy: 0.85<br/>F1: 0.82<br/>Status: Development]
            V1_Artifacts[model.pkl<br/>feature_importance.png<br/>requirements.txt]
        end

        subgraph V2["Version 2 - Staging"]
            V2_Metrics[Accuracy: 0.87<br/>F1: 0.85<br/>Status: Staging]
            V2_Artifacts[model.pkl<br/>confusion_matrix.png<br/>requirements.txt]
        end

        subgraph V3["Version 3 - Production ⭐"]
            V3_Metrics[Accuracy: 0.89<br/>F1: 0.87<br/>Status: Production]
            V3_Artifacts[model.pkl<br/>roc_curve.png<br/>requirements.txt]
        end
    end

    V1 -->|Promote| V2
    V2 -->|Promote| V3

    classDef devStyle fill:#e3f2fd,stroke:#1565c0,color:#000
    classDef stagingStyle fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef prodStyle fill:#e8f5e9,stroke:#2e7d32,color:#000

    class V1,V1_Metrics,V1_Artifacts devStyle
    class V2,V2_Metrics,V2_Artifacts stagingStyle
    class V3,V3_Metrics,V3_Artifacts prodStyle
```

---

## Sequence Diagrams

### Complete ML Workflow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI Gateway
    participant Airbyte
    participant Spark
    participant DBT
    participant Feast
    participant MLflow
    participant Model

    Note over User,Model: Phase 1: Data Ingestion
    User->>API: POST /datasource (Configure source)
    API->>Airbyte: Create connection
    Airbyte-->>API: connection_id

    User->>API: POST /ingestion (Start sync)
    API->>Airbyte: Trigger sync job
    activate Airbyte
    Airbyte->>Airbyte: Extract & Load
    Airbyte->>Airbyte: Write to Bronze
    deactivate Airbyte
    Airbyte-->>API: job_id

    Note over User,Model: Phase 2: Data Cleansing
    User->>API: POST /spark/transform
    API->>Spark: Create SparkApplication
    activate Spark
    Spark->>Spark: Read Bronze
    Spark->>Spark: Clean & Validate
    Spark->>Spark: Write to Silver
    deactivate Spark
    Spark-->>API: run_id

    Note over User,Model: Phase 3: Business Aggregation
    User->>API: POST /dbt/transform
    API->>DBT: Execute model
    activate DBT
    DBT->>DBT: Read Silver (via Trino)
    DBT->>DBT: Apply transformations
    DBT->>DBT: Write to Gold
    deactivate DBT
    DBT-->>API: transform_id

    Note over User,Model: Phase 4: Feature Registration
    User->>API: POST /feast/features
    API->>Feast: Register feature view
    Feast->>Feast: Query Iceberg for S3 path
    Feast->>Feast: Create FileSource (direct S3)
    Feast-->>API: feature_view_name

    Note over User,Model: Phase 5: Model Training
    User->>API: POST /mlops/training
    API->>MLflow: Submit training job
    activate MLflow
    MLflow->>Feast: Fetch features
    Feast-->>MLflow: Features DataFrame
    MLflow->>MLflow: Train model
    MLflow->>MLflow: Log metrics
    MLflow->>Model: Register model
    deactivate MLflow
    MLflow-->>API: run_id

    Note over User,Model: Phase 6: Inference
    User->>API: POST /mlops/inference
    API->>Model: Load model & predict
    Model-->>API: predictions
    API-->>User: results
```

### Spark Job Execution

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant Operator as Spark Operator
    participant Driver as Driver Pod
    participant Exec as Executor Pods
    participant S3 as S3 Storage

    API->>Operator: Create SparkApplication
    activate Operator
    Operator->>Driver: Create driver pod
    activate Driver

    Driver->>Driver: Initialize Spark Context
    Driver->>Operator: Request executors
    Operator->>Exec: Create executor pods
    activate Exec

    Driver->>Exec: Distribute tasks
    Exec->>S3: Read Bronze Parquet
    S3-->>Exec: Data partitions

    Exec->>Exec: Apply transformations
    Exec->>Exec: Aggregate results

    Exec->>S3: Write Silver Parquet
    S3-->>Exec: Write confirmed

    Exec-->>Driver: Task complete
    deactivate Exec

    Driver->>Operator: Job complete
    deactivate Driver
    Operator-->>API: Status: COMPLETED
    deactivate Operator
```

---

## Network & Storage Architecture

### Kubernetes Service Mesh

```mermaid
flowchart TB
    subgraph Internet["External Access"]
        Browser[Web Browser]
        Client[API Client]
    end

    subgraph Ingress["Ingress Layer"]
        NGINX[NGINX Ingress Controller]
        Rules["Routing Rules:<br>asgard.example.com → asgard-app:80<br>mlflow.example.com → mlflow:5000"]
    end

    subgraph Namespace["Kubernetes Namespace: asgard"]
        subgraph Services["Services (ClusterIP)"]
            SvcAPI[asgard-app<br>:80]
            SvcMLflow[mlflow-service<br>:5000]
            SvcPG[postgres<br>:5432]
            SvcTrino[trino<br>:8080]
            SvcAirbyte[airbyte-server<br>:8001]
        end

        subgraph Deployments["Deployments"]
            direction LR
            PodAPI1[asgard-app-1]
            PodAPI2[asgard-app-2]
            PodMLflow[mlflow-pod]
            PodTrino[trino-coordinator]
            PodAirbyte[airbyte-server]
        end

        subgraph StatefulSets["StatefulSets"]
            PodPG[postgres-0]
        end

        subgraph Storage["Storage"]
            PVC1[(PVC: mlflow-artifacts)]
            PVC2[(PVC: postgres-data)]
            S3[(S3: s3://airbytedestination1)]
        end
    end

    Browser & Client --> NGINX
    NGINX --> Rules
    Rules --> SvcAPI & SvcMLflow

    SvcAPI --> PodAPI1 & PodAPI2
    SvcMLflow --> PodMLflow
    SvcPG --> PodPG
    SvcTrino --> PodTrino
    SvcAirbyte --> PodAirbyte

    PodAPI1 & PodAPI2 -.-> SvcMLflow & SvcPG & SvcTrino & SvcAirbyte
    PodMLflow --> PVC1
    PodPG --> PVC2
    PodAPI1 & PodAPI2 & PodMLflow & PodTrino --> S3

    classDef externalStyle fill:#e3f2fd,stroke:#1565c0,color:#000
    classDef ingressStyle fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef serviceStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000
    classDef podStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef storageStyle fill:#fce4ec,stroke:#c2185b,color:#000

    class Browser,Client externalStyle
    class NGINX,Rules ingressStyle
    class SvcAPI,SvcMLflow,SvcPG,SvcTrino,SvcAirbyte serviceStyle
    class PodAPI1,PodAPI2,PodMLflow,PodTrino,PodAirbyte,PodPG podStyle
    class PVC1,PVC2,S3 storageStyle
```

### Service Communication

```

asgard-app Pod Communication:
├── http://mlflow-service:5000           (MLflow API)
├── http://trino:8080                    (Trino queries)
├── postgresql://postgres:5432/feast     (Feast registry)
├── postgresql://postgres:5432/mlflow    (MLflow metadata)
├── http://airbyte-server:8001           (Airbyte API)
└── s3://airbytedestination1             (S3 storage)
```

---

## Security

    -->> Performance

### Security Architecture

```mermaid
flowchart TB
    subgraph Security["Security Layers"]
        subgraph K8s["Kubernetes RBAC"]
            SA[ServiceAccounts]
            Roles[Roles  RoleBindings]
            NetPol[NetworkPolicies]
        end

        subgraph AWS["AWS IAM"]
            IAM[IAM Roles]
            Keys[Access Keys<br>in K8s Secrets]
            IRSA[IAM Roles for<br>Service Accounts]
        end

        subgraph App["Application Level"]
            Validation[Input Validation<br>Pydantic]
            Throttle[Rate Limiting]
            Auth[API Key Auth<br>Optional]
        end

        subgraph Data["Data Security"]
            EncryptRest[S3 Encryption at Rest<br>SSE-S3/SSE-KMS]
            EncryptTransit[TLS in Transit]
            Access[S3 IAM Policies]
        end
    end

    K8s --> AWS
    AWS --> App
    App --> Data

    classDef k8sStyle fill:#e3f2fd,stroke:#1565c0,color:#000
    classDef awsStyle fill:#fff3e0,stroke:#ef6c00,color:#000
    classDef appStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    classDef dataStyle fill:#f3e5f5,stroke:#6a1b9a,color:#000

    class K8s,SA,Roles,NetPol k8sStyle
    class AWS,IAM,Keys,IRSA awsStyle
    class App,Validation,Throttle,Auth appStyle
    class Data,EncryptRest,EncryptTransit,Access dataStyle
```

### Horizontal Scaling

```mermaid
flowchart LR
    subgraph Scaling["Horizontal Scaling Strategies"]
        subgraph API["FastAPI Gateway"]
            HPA1[Horizontal Pod Autoscaler\nMin: 2, Max: 10\nCPU: 70%]
        end

        subgraph Spark["Spark Jobs"]
            Dynamic[Dynamic Executor Allocation\nMin: 1, Max: 20\nLoad-based]
        end

        subgraph Trino["Trino Cluster"]
            Workers[Worker Pool Expansion\nAdd workers on demand]
        end

        subgraph Airbyte["Airbyte Workers"]
            Replicas[Worker Replicas\nScale based on sync queue]
        end

        subgraph MLflow["MLflow Server"]
            Stateless[Stateless Deployment\nCan scale pods freely]
        end
    end

    classDef scaleStyle fill:#e8f5e9,stroke:#2e7d32,color:#000
    class API,Spark,Trino,Airbyte,MLflow,HPA1,Dynamic,Workers,Replicas,Stateless scaleStyle
```

---

## Reference Tables

### Component Port Reference

| Component         | Internal Port | External Port       | Protocol   |
| ----------------- | ------------- | ------------------- | ---------- |
| Asgard API        | 80            | 8000 (port-forward) | HTTP       |
| MLflow Server     | 5000          | 5000 (port-forward) | HTTP       |
| PostgreSQL        | 5432          | -                   | PostgreSQL |
| Trino Coordinator | 8080          | -                   | HTTP       |
| Airbyte Server    | 8001          | 8001 (port-forward) | HTTP       |
| Spark Driver      | 4040          | 4040 (port-forward) | HTTP       |
| Spark UI          | 18080         | -                   | HTTP       |

### Iceberg Table Naming Convention

| Layer  | Namespace        | Table Pattern                | Example                            |
| ------ | ---------------- | ---------------------------- | ---------------------------------- |
| Bronze | `iceberg.bronze` | `{source_table}`             | `iceberg.bronze.customers`         |
| Silver | `iceberg.silver` | `{source_table}_cleaned`     | `iceberg.silver.customers_cleaned` |
| Gold   | `iceberg.gold`   | `{business_entity}_{metric}` | `iceberg.gold.customer_metrics`    |

### API Endpoint Summary

| Endpoint                 | Method | Purpose                | Response Time |
| ------------------------ | ------ | ---------------------- | ------------- |
| `/health`                | GET    | Platform health        | <50ms         |
| `/datasource`            | POST   | Create data source     | ~1s           |
| `/ingestion`             | POST   | Start sync job         | ~1s           |
| `/spark/transform`       | POST   | Submit Spark job       | ~2s           |
| `/dbt/transform`         | POST   | Run DBT model          | ~1s           |
| `/feast/features`        | POST   | Register features      | ~500ms        |
| `/mlops/training/upload` | POST   | Upload training script | ~2s           |
| `/mlops/inference`       | POST   | Make predictions       | <100ms        |

### Data Layer Comparison

| Aspect        | Bronze           | Silver             | Gold                 |
| ------------- | ---------------- | ------------------ | -------------------- |
| **Source**    | External systems | Bronze             | Silver               |
| **Quality**   | Raw, as-is       | Cleaned, validated | Aggregated, enriched |
| **Schema**    | Original         | Standardized       | ML-ready             |
| **Size**      | Largest          | Medium             | Smallest             |
| **Updates**   | Append-only      | Overwrite/append   | Usually overwrite    |
| **Consumers** | Spark            | DBT, analysts      | Feast, ML models     |

### Typical Processing Times

| Operation            | Volume    | Time      | Notes              |
| -------------------- | --------- | --------- | ------------------ |
| Airbyte Sync         | 100K rows | 10-15 min | Depends on network |
| Spark Cleansing      | 100K rows | 5-10 min  | 2 executors        |
| DBT Aggregation      | 100K rows | 3-5 min   | Simple joins       |
| Feature Registration | -         | <1 min    | Metadata only      |
| Model Training       | 100K rows | 15-30 min | Random Forest      |
| Batch Inference      | 100K rows | 5-10 min  | Depends on model   |

---

## Summary

### Key Architectural Highlights

1. ✅ **Unified API** - Single FastAPI gateway for all operations
2. ✅ **Zero Duplication** - Feast reads directly from Iceberg (no data copy)
3. ✅ **Medallion Architecture** - Bronze → Silver → Gold data layers
4. ✅ **Kubernetes Native** - Cloud-agnostic, horizontally scalable
5. ✅ **Open Source Stack** - No vendor lock-in
6. ✅ **Production Ready** - Battle-tested components
7. ✅ **Git-like Data Versioning** - Nessie catalog for data branches/tags
8. ✅ **ACID Transactions** - Iceberg ensures data consistency

### Platform Benefits

- **Single Source of Truth**: All features read from same Iceberg tables
- **Cost Efficient**: No duplicate storage, minimal data movement
- **Scalable**: S3 storage, Kubernetes orchestration, dynamic scaling
- **Developer Friendly**: REST API, auto-documentation, type safety
- **Production Grade**: Monitoring, logging, error handling built-in

---

**Document Status**: ✅ Complete and Ready  
**Diagrams**: ✅ All rendered with Mermaid  
**Last Review**: November 24, 2025
