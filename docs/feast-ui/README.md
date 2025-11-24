# Asgard Feast UI

**Interactive Feature Store Management & Visualization**

This folder contains scripts and utilities for running the Feast UI to visualize and manage features in the Asgard Data Platform.

---

## 📋 Overview

The Feast UI provides a web-based interface to:

- **Browse Feature Views** - Explore all registered feature views and their schemas
- **View Entities** - See entity definitions and relationships
- **Manage Feature Services** - Review feature services for ML models
- **Inspect Metadata** - View feature statistics, tags, and descriptions
- **Monitor Data Sources** - Check source configurations and health

---

## 📂 Files

### `start-asgard-feast-ui.sh`

**Purpose**: Main launcher script for the Feast UI

**What it does**:

1. Checks if Feast repository is initialized
2. Runs initial setup if needed (calls `setup_feast_repo.py`)
3. Displays currently registered features
4. Provides instructions for registering features via API
5. Launches Feast UI web server

**Usage**:

```bash
cd /home/hac/downloads/code/asgard-dev/docs/feast-ui
./start-asgard-feast-ui.sh
```

**Environment Variables**:

- `FEAST_UI_HOST` - Host to bind to (default: `0.0.0.0`)
- `FEAST_UI_PORT` - Port to listen on (default: `8888`)

**Example**:

```bash
FEAST_UI_HOST=127.0.0.1 FEAST_UI_PORT=9000 ./start-asgard-feast-ui.sh
```

### `setup_feast_repo.py`

**Purpose**: Python script to initialize and populate the Feast repository

**What it does**:

1. **Creates Feast repository structure**:

   - `/tmp/feast_repo/` - Main repository directory
   - `/tmp/feast_repo/data/` - Sample data storage
   - `/tmp/feast_repo/feature_store.yaml` - Configuration file
   - `/tmp/feast_repo/feature_definitions.py` - Feature definitions

2. **Generates sample data** (for demonstration):

   - `customer_features.parquet` - Customer metrics (purchases, avg value, etc.)
   - `product_features.parquet` - Product metrics (sales, ratings, reviews)
   - `order_features.parquet` - Order data (totals, items, status)

3. **Creates feature definitions**:

   - **Entities**: `customer`, `product`, `order`
   - **Feature Views**: `customer_features`, `product_features`, `order_features`
   - **Feature Services**: `customer_insights_v1`, `product_recommendations_v1`, `order_prediction_v1`

4. **Applies features** to the Feast registry

**Usage**:

```bash
cd /home/hac/downloads/code/asgard-dev/docs/feast-ui
uv run python setup_feast_repo.py
```

**Manual Run** (if needed):

```bash
python3 setup_feast_repo.py
```

---

## 🚀 Quick Start

### Prerequisites

1. **Install dependencies** (if not using `uv`):

   ```bash
   pip install feast pandas pyarrow
   ```

2. **Or use uv** (recommended):
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install feast pandas pyarrow
   ```

### Launch Feast UI

**Option 1: Using the launcher script** (recommended):

```bash
./start-asgard-feast-ui.sh
```

**Option 2: Manual setup**:

```bash
# 1. Setup repository
python3 setup_feast_repo.py

# 2. Launch UI
cd /tmp/feast_repo
feast ui -h 0.0.0.0 -p 8888
```

### Access the UI

Once started, open your browser:

- **Local**: http://localhost:8888
- **Network**: http://0.0.0.0:8888

---

## 🔧 Configuration

### Feast Repository Structure

```
/tmp/feast_repo/
├── feature_store.yaml          # Feast configuration
├── feature_definitions.py      # Feature view definitions
├── __init__.py                 # Python package marker
└── data/
    ├── registry.db            # Feature registry (SQLite)
    ├── online_store.db        # Online feature store (SQLite)
    ├── customer_features.parquet
    ├── product_features.parquet
    └── order_features.parquet
```

### `feature_store.yaml`

```yaml
project: asgard_feast
registry: data/registry.db
provider: local
online_store:
  type: sqlite
  path: data/online_store.db
entity_key_serialization_version: 3
auth:
  type: no_auth
```

---

## 📊 Sample Features

### Entities

| Entity     | Join Key      | Description                             |
| ---------- | ------------- | --------------------------------------- |
| `customer` | `customer_id` | Customer entity for e-commerce platform |
| `product`  | `product_id`  | Product entity for e-commerce catalog   |
| `order`    | `order_id`    | Order entity for transactions           |

### Feature Views

#### `customer_features`

- **Entity**: customer
- **TTL**: 1 day
- **Features**:
  - `total_purchases` (Float64) - Total purchase amount
  - `avg_purchase_value` (Float64) - Average purchase value
  - `last_purchase_days_ago` (Int64) - Days since last purchase
- **Source**: `customer_features.parquet`

#### `product_features`

- **Entity**: product
- **TTL**: 7 days
- **Features**:
  - `total_sales` (Float64) - Total sales amount
  - `avg_rating` (Float64) - Average customer rating
  - `review_count` (Int64) - Number of reviews
- **Source**: `product_features.parquet`

#### `order_features`

- **Entity**: order
- **TTL**: 12 hours
- **Features**:
  - `order_total` (Float64) - Order total amount
  - `item_count` (Int64) - Number of items in order
  - `is_completed` (Int64) - Order completion status
- **Source**: `order_features.parquet`

### Feature Services

#### `customer_insights_v1`

- **Purpose**: Customer purchasing insights for ML models
- **Features**:
  - `customer_features.total_purchases`
  - `customer_features.avg_purchase_value`

#### `product_recommendations_v1`

- **Purpose**: Product recommendation features
- **Features**:
  - `product_features.avg_rating`
  - `product_features.review_count`

#### `order_prediction_v1`

- **Purpose**: Features for order completion prediction
- **Features**:
  - All `customer_features`
  - `order_features.order_total`
  - `order_features.item_count`

---

## 🔗 Integration with Asgard Platform

### Registering Features via API

To register features from your Iceberg gold layer tables:

1. **Start the Asgard API** (in another terminal):

   ```bash
   cd /home/hac/downloads/code/asgard-dev
   uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Register a feature view**:

   ```bash
   curl -X POST http://localhost:8000/feast/features \
     -H "Content-Type: application/json" \
     -d '{
       "name": "customer_metrics",
       "entities": ["customer_id"],
       "features": [
         {"name": "total_orders", "dtype": "INT64"},
         {"name": "lifetime_value", "dtype": "FLOAT64"},
         {"name": "avg_order_value", "dtype": "FLOAT64"}
       ],
       "source": {
         "table_name": "customer_aggregates",
         "catalog": "iceberg",
         "schema": "gold",
         "timestamp_field": "updated_at"
       },
       "online": true
     }'
   ```

3. **Refresh the Feast UI** to see the new features

### API Endpoints

| Endpoint                 | Method | Description                |
| ------------------------ | ------ | -------------------------- |
| `/feast/features`        | POST   | Register new feature view  |
| `/feast/features/{name}` | GET    | Get feature view details   |
| `/feast/features`        | GET    | List all feature views     |
| `/feast/status`          | GET    | Check Feast service status |

---

## 🛠️ Feast CLI Commands

```bash
# Navigate to feast repo
cd /tmp/feast_repo

# List feature views
feast feature-views list

# Describe a feature view
feast feature-views describe customer_features

# List entities
feast entities list

# List feature services
feast feature-services list

# Apply feature definitions (after changes)
feast apply

# Materialize features to online store
feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")

# Get online features
feast online-features get \
  --feature-service customer_insights_v1 \
  --entity customer_id=1
```

---

## 🧪 Testing Features

### Get Historical Features

```python
from feast import FeatureStore
import pandas as pd

# Initialize feature store
store = FeatureStore(repo_path="/tmp/feast_repo")

# Create entity dataframe
entity_df = pd.DataFrame({
    "customer_id": [1, 2, 3],
    "event_timestamp": [
        pd.Timestamp("2025-10-05"),
        pd.Timestamp("2025-10-05"),
        pd.Timestamp("2025-10-05")
    ]
})

# Get historical features
features = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "customer_features:total_purchases",
        "customer_features:avg_purchase_value",
    ],
).to_df()

print(features)
```

### Get Online Features

```python
from feast import FeatureStore

store = FeatureStore(repo_path="/tmp/feast_repo")

# Get online features for a customer
features = store.get_online_features(
    features=[
        "customer_features:total_purchases",
        "customer_features:avg_purchase_value",
    ],
    entity_rows=[
        {"customer_id": 1},
        {"customer_id": 2},
    ],
).to_dict()

print(features)
```

---

## 📝 Customization

### Adding New Feature Views

1. **Edit** `feature_definitions.py`:

   ```python
   # Add new entity
   transaction = Entity(
       name="transaction",
       join_keys=["transaction_id"],
       description="Transaction entity"
   )

   # Add new source
   transaction_source = FileSource(
       name="transaction_stats",
       path="data/transaction_features.parquet",
       timestamp_field="event_timestamp",
   )

   # Add new feature view
   transaction_fv = FeatureView(
       name="transaction_features",
       entities=[transaction],
       ttl=timedelta(hours=24),
       schema=[
           Field(name="amount", dtype=Float64),
           Field(name="status", dtype=String),
       ],
       source=transaction_source,
   )
   ```

2. **Apply changes**:

   ```bash
   cd /tmp/feast_repo
   feast apply
   ```

3. **Refresh UI** to see new features

---

## 🐛 Troubleshooting

### UI Not Starting

**Problem**: Feast UI fails to start

```bash
Error: No module named 'feast'
```

**Solution**: Install Feast

```bash
pip install feast
# or
uv pip install feast
```

### Features Not Showing

**Problem**: UI shows no features

**Solution**: Run setup script

```bash
python3 setup_feast_repo.py
```

### Registry Errors

**Problem**: Registry database errors

```bash
Error: registry.db is locked
```

**Solution**: Remove and recreate registry

```bash
rm -f /tmp/feast_repo/data/registry.db
cd /tmp/feast_repo
feast apply
```

### Port Already in Use

**Problem**: Port 8888 already taken

```bash
Error: Address already in use
```

**Solution**: Use a different port

```bash
FEAST_UI_PORT=9000 ./start-asgard-feast-ui.sh
```

---

## 🔍 Advanced Usage

### Custom Feast Repository Location

To use a different location:

```bash
# Modify setup_feast_repo.py
FEAST_REPO_PATH = Path("/custom/path/feast_repo")

# Or set environment variable before running
export FEAST_REPO="/custom/path/feast_repo"
```

### Using with Production Data

Replace sample data with actual Iceberg tables:

```python
from feast import FileSource

# Point to Iceberg S3 paths
customer_source = FileSource(
    name="customer_gold",
    path="s3a://airbytedestination1/iceberg/gold/customer_metrics/data/*.parquet",
    timestamp_field="updated_at",
)
```

### Enable Authentication

Update `feature_store.yaml`:

```yaml
auth:
  type: oidc
  client_id: your_client_id
  client_secret: your_client_secret
  auth_discovery_url: https://your-auth-server/.well-known/openid-configuration
```

---

## 📚 Additional Resources

- **Feast Documentation**: https://docs.feast.dev
- **Feast GitHub**: https://github.com/feast-dev/feast
- **Asgard Platform Docs**: [../COMPLETE_ARCHITECTURE.md](../COMPLETE_ARCHITECTURE.md)
- **Feast API Reference**: [../../app/feast/README.md](../../app/feast/README.md)

---

## 🎯 Summary

The Feast UI setup provides:

✅ **Quick Setup** - One-command launch with sample data  
✅ **Visual Interface** - Web-based feature exploration  
✅ **API Integration** - Seamless connection to Asgard platform  
✅ **Sample Features** - Pre-configured customer, product, and order features  
✅ **Production Ready** - Can connect to real Iceberg tables

**Start exploring your features now!** 🚀
