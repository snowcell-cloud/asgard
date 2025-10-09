#!/usr/bin/env python3
"""
Setup Feast Feature Repository for Asgard
This script creates a proper Feast feature repository with example features
that can be viewed in the Feast UI.
"""

import os
from pathlib import Path
from datetime import timedelta
import pandas as pd
from feast import Entity, FeatureView, Field, FileSource, FeatureStore
from feast.types import Float64, Int64, String

# Configuration
FEAST_REPO_PATH = Path("/tmp/feast_repo")
DATA_DIR = FEAST_REPO_PATH / "data"


def setup_feast_repo():
    """Setup Feast repository structure."""
    print("🔧 Setting up Feast repository...")

    # Create directories
    FEAST_REPO_PATH.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    # Create feature_store.yaml
    feature_store_yaml = """project: asgard_feast
registry: data/registry.db
provider: local
online_store:
    type: sqlite
    path: data/online_store.db
entity_key_serialization_version: 3
auth:
    type: no_auth
"""

    with open(FEAST_REPO_PATH / "feature_store.yaml", "w") as f:
        f.write(feature_store_yaml)

    print(f"✅ Created feature_store.yaml at {FEAST_REPO_PATH}")

    # Create __init__.py
    (FEAST_REPO_PATH / "__init__.py").touch()

    return FEAST_REPO_PATH


def create_sample_data():
    """Create sample data files for demonstration."""
    print("\n📊 Creating sample data...")

    # Sample customer data
    customer_data = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "total_purchases": [150.5, 320.0, 89.99, 450.25, 210.0],
            "avg_purchase_value": [50.17, 64.0, 29.99, 75.04, 52.5],
            "last_purchase_days_ago": [5, 12, 30, 2, 8],
            "event_timestamp": pd.to_datetime(
                ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05"]
            ),
            "created": pd.to_datetime(
                ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05"]
            ),
        }
    )

    customer_file = DATA_DIR / "customer_features.parquet"
    customer_data.to_parquet(customer_file, index=False)
    print(f"✅ Created {customer_file}")

    # Sample product data
    product_data = pd.DataFrame(
        {
            "product_id": ["P1", "P2", "P3", "P4", "P5"],
            "total_sales": [5000.0, 3200.0, 1500.0, 8900.0, 4200.0],
            "avg_rating": [4.5, 4.2, 3.8, 4.9, 4.1],
            "review_count": [120, 85, 45, 310, 95],
            "event_timestamp": pd.to_datetime(
                ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05"]
            ),
            "created": pd.to_datetime(
                ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05"]
            ),
        }
    )

    product_file = DATA_DIR / "product_features.parquet"
    product_data.to_parquet(product_file, index=False)
    print(f"✅ Created {product_file}")

    # Sample order data
    order_data = pd.DataFrame(
        {
            "order_id": [1001, 1002, 1003, 1004, 1005],
            "customer_id": [1, 2, 3, 1, 4],
            "order_total": [150.5, 320.0, 89.99, 200.0, 450.25],
            "item_count": [3, 5, 1, 2, 7],
            "is_completed": [1, 1, 0, 1, 1],
            "event_timestamp": pd.to_datetime(
                ["2025-10-05", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09"]
            ),
            "created": pd.to_datetime(
                ["2025-10-05", "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09"]
            ),
        }
    )

    order_file = DATA_DIR / "order_features.parquet"
    order_data.to_parquet(order_file, index=False)
    print(f"✅ Created {order_file}")

    return {"customer": str(customer_file), "product": str(product_file), "order": str(order_file)}


def create_feature_definitions(data_files):
    """Create feature_definitions.py file."""
    print("\n📝 Creating feature definitions...")

    feature_definitions = f'''"""
Asgard Feast Feature Definitions
Auto-generated feature views for the Asgard Data Platform
"""

from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, FeatureService
from feast.types import Float64, Int64, String

# ============================================================================
# ENTITIES
# ============================================================================

customer = Entity(
    name="customer",
    join_keys=["customer_id"],
    description="Customer entity for e-commerce platform"
)

product = Entity(
    name="product",
    join_keys=["product_id"],
    description="Product entity for e-commerce catalog"
)

order = Entity(
    name="order",
    join_keys=["order_id"],
    description="Order entity for transactions"
)

# ============================================================================
# DATA SOURCES
# ============================================================================

customer_source = FileSource(
    name="customer_stats_source",
    path="data/customer_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

product_source = FileSource(
    name="product_stats_source",
    path="data/product_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

order_source = FileSource(
    name="order_stats_source",
    path="data/order_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

# ============================================================================
# FEATURE VIEWS
# ============================================================================

customer_features_fv = FeatureView(
    name="customer_features",
    entities=[customer],
    ttl=timedelta(days=1),
    schema=[
        Field(name="total_purchases", dtype=Float64, description="Total purchase amount"),
        Field(name="avg_purchase_value", dtype=Float64, description="Average purchase value"),
        Field(name="last_purchase_days_ago", dtype=Int64, description="Days since last purchase"),
    ],
    online=True,
    source=customer_source,
    tags={{
        "team": "data_platform",
        "source": "gold_layer",
        "domain": "customer"
    }},
)

product_features_fv = FeatureView(
    name="product_features",
    entities=[product],
    ttl=timedelta(days=7),
    schema=[
        Field(name="total_sales", dtype=Float64, description="Total sales amount"),
        Field(name="avg_rating", dtype=Float64, description="Average customer rating"),
        Field(name="review_count", dtype=Int64, description="Number of reviews"),
    ],
    online=True,
    source=product_source,
    tags={{
        "team": "data_platform",
        "source": "gold_layer",
        "domain": "product"
    }},
)

order_features_fv = FeatureView(
    name="order_features",
    entities=[order],
    ttl=timedelta(hours=12),
    schema=[
        Field(name="order_total", dtype=Float64, description="Order total amount"),
        Field(name="item_count", dtype=Int64, description="Number of items in order"),
        Field(name="is_completed", dtype=Int64, description="Order completion status"),
    ],
    online=True,
    source=order_source,
    tags={{
        "team": "data_platform",
        "source": "gold_layer",
        "domain": "order"
    }},
)

# ============================================================================
# FEATURE SERVICES
# ============================================================================

customer_insights_v1 = FeatureService(
    name="customer_insights_v1",
    features=[
        customer_features_fv[["total_purchases", "avg_purchase_value"]],
    ],
    description="Customer purchasing insights for ML models v1"
)

product_recommendations_v1 = FeatureService(
    name="product_recommendations_v1",
    features=[
        product_features_fv[["avg_rating", "review_count"]],
    ],
    description="Product recommendation features v1"
)

order_prediction_v1 = FeatureService(
    name="order_prediction_v1",
    features=[
        customer_features_fv,
        order_features_fv[["order_total", "item_count"]],
    ],
    description="Features for order completion prediction v1"
)
'''

    definitions_file = FEAST_REPO_PATH / "feature_definitions.py"
    with open(definitions_file, "w") as f:
        f.write(feature_definitions)

    print(f"✅ Created {definitions_file}")
    return definitions_file


def apply_features():
    """Apply features to the registry."""
    print("\n🚀 Applying features to Feast registry...")

    # Change to feast repo directory
    os.chdir(FEAST_REPO_PATH)

    # Initialize FeatureStore
    store = FeatureStore(repo_path=str(FEAST_REPO_PATH))

    # Apply all features
    os.system("feast apply")

    print("✅ Features applied successfully!")


def list_features():
    """List all registered features."""
    print("\n📋 Registered Features:")
    print("=" * 60)

    os.chdir(FEAST_REPO_PATH)

    print("\n🔹 Feature Views:")
    os.system("feast feature-views list")

    print("\n🔹 Entities:")
    os.system("feast entities list")

    print("\n🔹 Feature Services:")
    os.system("feast feature-services list")


def main():
    """Main setup function."""
    print("🎯 Asgard Feast Feature Store Setup")
    print("=" * 60)

    # Setup repository
    repo_path = setup_feast_repo()

    # Create sample data
    data_files = create_sample_data()

    # Create feature definitions
    create_feature_definitions(data_files)

    # Apply features
    apply_features()

    # List features
    list_features()

    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("\n📍 Feast repository location: " + str(FEAST_REPO_PATH))
    print("\n🌐 To view in Feast UI, run:")
    print(f"   cd {FEAST_REPO_PATH}")
    print("   feast ui -h 0.0.0.0 -p 8888")
    print("\n   Then open: http://localhost:8888")
    print("=" * 60)


if __name__ == "__main__":
    main()
