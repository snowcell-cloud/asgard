# Feast Feature Store API - Complete Demo Guide

**Purpose:** Client demonstration of Feast Feature Store integration with Iceberg  
**Date:** November 4, 2025  
**Status:** Production Ready ✅

---

## 📋 Table of Contents

1. [Quick Setup](#quick-setup)
2. [API Endpoint Overview](#api-endpoint-overview)
3. [Demo Scenario 1: E-Commerce Customer Features](#demo-scenario-1-e-commerce-customer-features)
4. [Demo Scenario 2: Product Recommendation Features](#demo-scenario-2-product-recommendation-features)
5. [Demo Scenario 3: Financial Transaction Features](#demo-scenario-3-financial-transaction-features)
6. [Complete cURL Examples](#complete-curl-examples)
7. [Python Client Examples](#python-client-examples)
8. [Postman Collection](#postman-collection)

---

## Quick Setup

### Port Forward Services

```bash
# Forward Asgard API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# Verify connectivity
curl http://localhost:8000/feast/status
```

### Expected Response

```json
{
  "registry_type": "sql",
  "store_type": "feast",
  "feature_views_count": 0,
  "entities_count": 0,
  "feature_services_count": 0,
  "feature_views": [],
  "entities": [],
  "feature_services": []
}
```

---

## API Endpoint Overview

| Endpoint                  | Method | Purpose                  | Demo Priority |
| ------------------------- | ------ | ------------------------ | ------------- |
| `/feast/status`           | GET    | Get feature store status | ⭐⭐⭐ High   |
| `/feast/features`         | POST   | Create feature view      | ⭐⭐⭐ High   |
| `/feast/features`         | GET    | List all feature views   | ⭐⭐⭐ High   |
| `/feast/features/service` | POST   | Create feature service   | ⭐⭐ Medium   |

---

## Demo Scenario 1: E-Commerce Customer Features

### Use Case

Predict customer churn using behavioral and transactional features from the Iceberg gold layer.

### Step 1: Check Feature Store Status

```bash
curl -X GET http://localhost:8000/feast/status | jq
```

**Expected Response:**

```json
{
  "registry_type": "sql",
  "store_type": "feast",
  "feature_views_count": 0,
  "entities_count": 0,
  "feature_services_count": 0,
  "feature_views": [],
  "entities": [],
  "feature_services": []
}
```

### Step 2: Create Customer Behavioral Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_behavior_features",
    "entities": ["customer_id"],
    "features": [
      {
        "name": "total_purchases",
        "dtype": "int64",
        "description": "Total number of purchases made by customer"
      },
      {
        "name": "avg_purchase_value",
        "dtype": "float64",
        "description": "Average value per purchase"
      },
      {
        "name": "days_since_last_purchase",
        "dtype": "int32",
        "description": "Number of days since last purchase"
      },
      {
        "name": "customer_lifetime_value",
        "dtype": "float64",
        "description": "Total revenue from customer"
      },
      {
        "name": "purchase_frequency",
        "dtype": "float64",
        "description": "Average purchases per month"
      }
    ],
    "source": {
      "table_name": "customer_metrics",
      "timestamp_field": "updated_at",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 2592000,
    "description": "Customer behavioral metrics for churn prediction",
    "tags": {
      "team": "data-science",
      "use_case": "churn_prediction",
      "version": "1.0"
    },
    "online": false
  }'
```

**Expected Response:**

```json
{
  "name": "customer_behavior_features",
  "entities": ["customer_id"],
  "features": [
    "total_purchases",
    "avg_purchase_value",
    "days_since_last_purchase",
    "customer_lifetime_value",
    "purchase_frequency"
  ],
  "source_table": "iceberg.gold.customer_metrics",
  "online_enabled": false,
  "created_at": "2025-11-04T10:00:00",
  "status": "registered",
  "message": "Feature view registered successfully"
}
```

### Step 3: Create Customer Support Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_support_features",
    "entities": ["customer_id"],
    "features": [
      {
        "name": "support_tickets_count",
        "dtype": "int32",
        "description": "Total number of support tickets"
      },
      {
        "name": "avg_ticket_resolution_hours",
        "dtype": "float64",
        "description": "Average time to resolve tickets in hours"
      },
      {
        "name": "satisfaction_score",
        "dtype": "float64",
        "description": "Customer satisfaction score (1-5)"
      },
      {
        "name": "days_since_last_contact",
        "dtype": "int32",
        "description": "Days since last support contact"
      }
    ],
    "source": {
      "table_name": "support_metrics",
      "timestamp_field": "last_updated",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 604800,
    "description": "Customer support interaction features",
    "tags": {
      "team": "customer-success",
      "use_case": "churn_prediction",
      "version": "1.0"
    },
    "online": false
  }'
```

### Step 4: Create Feature Service (Grouping)

```bash
curl -X POST http://localhost:8000/feast/features/service \
  -H "Content-Type: application/json" \
  -d '{
    "name": "churn_prediction_service",
    "feature_views": [
      "customer_behavior_features",
      "customer_support_features"
    ],
    "description": "Complete feature set for customer churn prediction model",
    "tags": {
      "model": "churn_predictor_v1",
      "team": "data-science"
    }
  }'
```

**Expected Response:**

```json
{
  "name": "churn_prediction_service",
  "feature_views": ["customer_behavior_features", "customer_support_features"],
  "created_at": "2025-11-04T10:05:00",
  "status": "registered"
}
```

### Step 5: List All Feature Views

```bash
curl -X GET http://localhost:8000/feast/features | jq
```

**Expected Response:**

```json
[
  {
    "name": "customer_behavior_features",
    "entities": ["customer_id"],
    "features": [
      {
        "name": "total_purchases",
        "dtype": "int64",
        "description": "Total number of purchases made by customer"
      },
      {
        "name": "avg_purchase_value",
        "dtype": "float64",
        "description": "Average value per purchase"
      },
      {
        "name": "days_since_last_purchase",
        "dtype": "int32",
        "description": "Number of days since last purchase"
      },
      {
        "name": "customer_lifetime_value",
        "dtype": "float64",
        "description": "Total revenue from customer"
      },
      {
        "name": "purchase_frequency",
        "dtype": "float64",
        "description": "Average purchases per month"
      }
    ],
    "ttl_seconds": 2592000,
    "online_enabled": false,
    "source_table": "iceberg.gold.customer_metrics",
    "tags": {
      "team": "data-science",
      "use_case": "churn_prediction",
      "version": "1.0"
    }
  },
  {
    "name": "customer_support_features",
    "entities": ["customer_id"],
    "features": [
      {
        "name": "support_tickets_count",
        "dtype": "int32",
        "description": "Total number of support tickets"
      },
      {
        "name": "avg_ticket_resolution_hours",
        "dtype": "float64",
        "description": "Average time to resolve tickets in hours"
      },
      {
        "name": "satisfaction_score",
        "dtype": "float64",
        "description": "Customer satisfaction score (1-5)"
      },
      {
        "name": "days_since_last_contact",
        "dtype": "int32",
        "description": "Days since last support contact"
      }
    ],
    "ttl_seconds": 604800,
    "online_enabled": false,
    "source_table": "iceberg.gold.support_metrics",
    "tags": {
      "team": "customer-success",
      "use_case": "churn_prediction",
      "version": "1.0"
    }
  }
]
```

---

## Demo Scenario 2: Product Recommendation Features

### Use Case

Build product recommendation system using product interaction and inventory features.

### Step 1: Create Product Interaction Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "product_interaction_features",
    "entities": ["product_id"],
    "features": [
      {
        "name": "view_count_7d",
        "dtype": "int64",
        "description": "Product views in last 7 days"
      },
      {
        "name": "add_to_cart_count_7d",
        "dtype": "int64",
        "description": "Add to cart events in last 7 days"
      },
      {
        "name": "purchase_count_7d",
        "dtype": "int64",
        "description": "Purchases in last 7 days"
      },
      {
        "name": "conversion_rate",
        "dtype": "float64",
        "description": "View to purchase conversion rate"
      },
      {
        "name": "avg_rating",
        "dtype": "float64",
        "description": "Average product rating (1-5)"
      },
      {
        "name": "review_count",
        "dtype": "int32",
        "description": "Total number of reviews"
      }
    ],
    "source": {
      "table_name": "product_interactions",
      "timestamp_field": "event_time",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 604800,
    "description": "Product interaction metrics for recommendation engine",
    "tags": {
      "team": "ml-platform",
      "use_case": "product_recommendations",
      "refresh_frequency": "hourly"
    },
    "online": false
  }'
```

### Step 2: Create Product Inventory Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "product_inventory_features",
    "entities": ["product_id"],
    "features": [
      {
        "name": "stock_quantity",
        "dtype": "int32",
        "description": "Current stock quantity"
      },
      {
        "name": "days_in_stock",
        "dtype": "int32",
        "description": "Days product has been in inventory"
      },
      {
        "name": "price_current",
        "dtype": "float64",
        "description": "Current price"
      },
      {
        "name": "discount_percentage",
        "dtype": "float64",
        "description": "Current discount percentage"
      },
      {
        "name": "is_trending",
        "dtype": "bool",
        "description": "Whether product is currently trending"
      }
    ],
    "source": {
      "table_name": "inventory_status",
      "timestamp_field": "snapshot_time",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 86400,
    "description": "Real-time product inventory and pricing features",
    "tags": {
      "team": "inventory",
      "use_case": "product_recommendations",
      "refresh_frequency": "real-time"
    },
    "online": false
  }'
```

### Step 3: Create Recommendation Feature Service

```bash
curl -X POST http://localhost:8000/feast/features/service \
  -H "Content-Type: application/json" \
  -d '{
    "name": "product_recommendation_service",
    "feature_views": [
      "product_interaction_features",
      "product_inventory_features"
    ],
    "description": "Combined features for product recommendation ML model",
    "tags": {
      "model": "recommendation_engine_v2",
      "team": "ml-platform"
    }
  }'
```

---

## Demo Scenario 3: Financial Transaction Features

### Use Case

Fraud detection using transaction patterns and account behavior.

### Step 1: Create Transaction Pattern Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "transaction_pattern_features",
    "entities": ["account_id"],
    "features": [
      {
        "name": "transaction_count_24h",
        "dtype": "int32",
        "description": "Number of transactions in last 24 hours"
      },
      {
        "name": "total_amount_24h",
        "dtype": "float64",
        "description": "Total transaction amount in last 24 hours"
      },
      {
        "name": "avg_transaction_amount",
        "dtype": "float64",
        "description": "Average transaction amount"
      },
      {
        "name": "max_single_transaction",
        "dtype": "float64",
        "description": "Largest single transaction amount"
      },
      {
        "name": "unique_merchants_24h",
        "dtype": "int32",
        "description": "Number of unique merchants in 24h"
      },
      {
        "name": "foreign_transaction_count",
        "dtype": "int32",
        "description": "Number of foreign transactions"
      },
      {
        "name": "high_risk_merchant_count",
        "dtype": "int32",
        "description": "Transactions with high-risk merchants"
      }
    ],
    "source": {
      "table_name": "transaction_patterns",
      "timestamp_field": "pattern_timestamp",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 86400,
    "description": "Transaction pattern features for fraud detection",
    "tags": {
      "team": "risk-management",
      "use_case": "fraud_detection",
      "pii": "false",
      "compliance": "pci-dss"
    },
    "online": false
  }'
```

### Step 2: Create Account Risk Features

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "account_risk_features",
    "entities": ["account_id"],
    "features": [
      {
        "name": "account_age_days",
        "dtype": "int32",
        "description": "Days since account creation"
      },
      {
        "name": "failed_login_attempts_7d",
        "dtype": "int32",
        "description": "Failed login attempts in last 7 days"
      },
      {
        "name": "password_changes_30d",
        "dtype": "int32",
        "description": "Number of password changes in 30 days"
      },
      {
        "name": "verified_email",
        "dtype": "bool",
        "description": "Whether email is verified"
      },
      {
        "name": "verified_phone",
        "dtype": "bool",
        "description": "Whether phone is verified"
      },
      {
        "name": "risk_score",
        "dtype": "float64",
        "description": "Computed risk score (0-100)"
      },
      {
        "name": "previous_fraud_flags",
        "dtype": "int32",
        "description": "Number of previous fraud alerts"
      }
    ],
    "source": {
      "table_name": "account_security",
      "timestamp_field": "assessed_at",
      "catalog": "iceberg",
      "schema": "gold"
    },
    "ttl_seconds": 3600,
    "description": "Account-level security and risk features",
    "tags": {
      "team": "security",
      "use_case": "fraud_detection",
      "pii": "true",
      "compliance": "gdpr,pci-dss"
    },
    "online": false
  }'
```

### Step 3: Create Fraud Detection Feature Service

```bash
curl -X POST http://localhost:8000/feast/features/service \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fraud_detection_service",
    "feature_views": [
      "transaction_pattern_features",
      "account_risk_features"
    ],
    "description": "Real-time fraud detection feature service",
    "tags": {
      "model": "fraud_detector_v3",
      "team": "risk-management",
      "compliance": "pci-dss,sox"
    }
  }'
```

---

## Complete cURL Examples

### 1. Get Status (Check System Health)

```bash
curl -X GET http://localhost:8000/feast/status \
  -H "Accept: application/json" | jq
```

### 2. Create Feature View (Minimal Example)

```bash
curl -X POST http://localhost:8000/feast/features \
  -H "Content-Type: application/json" \
  -d '{
    "name": "simple_user_features",
    "entities": ["user_id"],
    "features": [
      {"name": "age", "dtype": "int32"},
      {"name": "account_balance", "dtype": "float64"}
    ],
    "source": {
      "table_name": "users",
      "catalog": "iceberg",
      "schema": "gold"
    }
  }'
```

### 3. List All Feature Views

```bash
curl -X GET http://localhost:8000/feast/features \
  -H "Accept: application/json" | jq
```

### 4. Create Feature Service

```bash
curl -X POST http://localhost:8000/feast/features/service \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_ml_service",
    "feature_views": ["simple_user_features"],
    "description": "Feature service for my ML model"
  }'
```

---

## Python Client Examples

### Setup

```python
import requests
import json
from typing import Dict, List, Any

class FeastAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.feast_url = f"{base_url}/feast"

    def get_status(self) -> Dict:
        """Get feature store status."""
        response = requests.get(f"{self.feast_url}/status")
        response.raise_for_status()
        return response.json()

    def create_feature_view(
        self,
        name: str,
        entities: List[str],
        features: List[Dict[str, str]],
        source_table: str,
        catalog: str = "iceberg",
        schema: str = "gold",
        **kwargs
    ) -> Dict:
        """Create a new feature view."""
        payload = {
            "name": name,
            "entities": entities,
            "features": features,
            "source": {
                "table_name": source_table,
                "catalog": catalog,
                "schema": schema
            },
            **kwargs
        }

        response = requests.post(
            f"{self.feast_url}/features",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def list_feature_views(self) -> List[Dict]:
        """List all feature views."""
        response = requests.get(f"{self.feast_url}/features")
        response.raise_for_status()
        return response.json()

    def create_feature_service(
        self,
        name: str,
        feature_views: List[str],
        description: str = None,
        tags: Dict[str, str] = None
    ) -> Dict:
        """Create a feature service."""
        payload = {
            "name": name,
            "feature_views": feature_views
        }

        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags

        response = requests.post(
            f"{self.feast_url}/features/service",
            json=payload
        )
        response.raise_for_status()
        return response.json()
```

### Example Usage

```python
# Initialize client
client = FeastAPIClient()

# 1. Check status
status = client.get_status()
print(f"Feature views: {status['feature_views_count']}")

# 2. Create customer features
customer_features = client.create_feature_view(
    name="customer_demographics",
    entities=["customer_id"],
    features=[
        {"name": "age", "dtype": "int32", "description": "Customer age"},
        {"name": "income", "dtype": "float64", "description": "Annual income"},
        {"name": "city", "dtype": "string", "description": "City of residence"}
    ],
    source_table="customer_profile",
    ttl_seconds=2592000,
    description="Customer demographic features",
    tags={"team": "marketing", "version": "1.0"}
)

print(f"Created: {customer_features['name']}")

# 3. List all feature views
views = client.list_feature_views()
for view in views:
    print(f"- {view['name']}: {len(view['features'])} features")

# 4. Create feature service
service = client.create_feature_service(
    name="marketing_campaign_service",
    feature_views=["customer_demographics"],
    description="Features for marketing campaign targeting",
    tags={"campaign": "q4_2025"}
)

print(f"Service created: {service['name']}")
```

### Complete Demo Script

```python
#!/usr/bin/env python3
"""
Feast API Demo Script
Demonstrates all Feast endpoints with realistic examples.
"""

from feast_client import FeastAPIClient
import time

def main():
    client = FeastAPIClient()

    print("=" * 60)
    print("FEAST FEATURE STORE API DEMO")
    print("=" * 60)

    # Step 1: Check initial status
    print("\n1️⃣  Checking Feature Store Status...")
    status = client.get_status()
    print(f"   ✓ Registry type: {status['registry_type']}")
    print(f"   ✓ Feature views: {status['feature_views_count']}")
    print(f"   ✓ Entities: {status['entities_count']}")

    # Step 2: Create customer behavior features
    print("\n2️⃣  Creating Customer Behavior Features...")
    behavior = client.create_feature_view(
        name="customer_behavior",
        entities=["customer_id"],
        features=[
            {
                "name": "total_purchases",
                "dtype": "int64",
                "description": "Total purchases"
            },
            {
                "name": "avg_order_value",
                "dtype": "float64",
                "description": "Average order value"
            },
            {
                "name": "days_since_last_order",
                "dtype": "int32",
                "description": "Days since last order"
            }
        ],
        source_table="customer_metrics",
        ttl_seconds=2592000,
        description="Customer purchase behavior features",
        tags={"team": "analytics", "version": "1.0"}
    )
    print(f"   ✓ Created: {behavior['name']}")
    print(f"   ✓ Features: {', '.join(behavior['features'])}")

    # Step 3: Create customer support features
    print("\n3️⃣  Creating Customer Support Features...")
    support = client.create_feature_view(
        name="customer_support",
        entities=["customer_id"],
        features=[
            {
                "name": "ticket_count",
                "dtype": "int32",
                "description": "Total support tickets"
            },
            {
                "name": "satisfaction_score",
                "dtype": "float64",
                "description": "CSAT score (1-5)"
            }
        ],
        source_table="support_metrics",
        ttl_seconds=604800,
        description="Customer support interaction features"
    )
    print(f"   ✓ Created: {support['name']}")

    # Step 4: List all feature views
    print("\n4️⃣  Listing All Feature Views...")
    views = client.list_feature_views()
    for i, view in enumerate(views, 1):
        print(f"   {i}. {view['name']}")
        print(f"      - Features: {len(view['features'])}")
        print(f"      - Entities: {', '.join(view['entities'])}")
        print(f"      - Source: {view['source_table']}")

    # Step 5: Create feature service
    print("\n5️⃣  Creating Feature Service...")
    service = client.create_feature_service(
        name="churn_prediction_service",
        feature_views=["customer_behavior", "customer_support"],
        description="Complete feature set for churn prediction",
        tags={"model": "churn_v1", "team": "ml"}
    )
    print(f"   ✓ Service: {service['name']}")
    print(f"   ✓ Includes: {len(service['feature_views'])} feature views")

    # Step 6: Final status check
    print("\n6️⃣  Final Status Check...")
    final_status = client.get_status()
    print(f"   ✓ Total feature views: {final_status['feature_views_count']}")
    print(f"   ✓ Total entities: {final_status['entities_count']}")
    print(f"   ✓ Total feature services: {final_status['feature_services_count']}")

    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## Postman Collection

### Import Instructions

1. Open Postman
2. Click **Import**
3. Paste the JSON below
4. Collection will be ready to use

### Collection JSON

```json
{
  "info": {
    "name": "Feast Feature Store API - Demo",
    "description": "Complete Feast API demonstration collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8000",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "1. Get Status",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/feast/status",
          "host": ["{{baseUrl}}"],
          "path": ["feast", "status"]
        }
      }
    },
    {
      "name": "2. Create Customer Features",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"name\": \"customer_behavior_features\",\n  \"entities\": [\"customer_id\"],\n  \"features\": [\n    {\n      \"name\": \"total_purchases\",\n      \"dtype\": \"int64\",\n      \"description\": \"Total purchases\"\n    },\n    {\n      \"name\": \"avg_purchase_value\",\n      \"dtype\": \"float64\",\n      \"description\": \"Average purchase value\"\n    },\n    {\n      \"name\": \"days_since_last_purchase\",\n      \"dtype\": \"int32\",\n      \"description\": \"Days since last purchase\"\n    }\n  ],\n  \"source\": {\n    \"table_name\": \"customer_metrics\",\n    \"timestamp_field\": \"updated_at\",\n    \"catalog\": \"iceberg\",\n    \"schema\": \"gold\"\n  },\n  \"ttl_seconds\": 2592000,\n  \"description\": \"Customer behavioral features\",\n  \"tags\": {\n    \"team\": \"data-science\",\n    \"version\": \"1.0\"\n  },\n  \"online\": false\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/feast/features",
          "host": ["{{baseUrl}}"],
          "path": ["feast", "features"]
        }
      }
    },
    {
      "name": "3. Create Product Features",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"name\": \"product_features\",\n  \"entities\": [\"product_id\"],\n  \"features\": [\n    {\n      \"name\": \"view_count_7d\",\n      \"dtype\": \"int64\",\n      \"description\": \"Views in last 7 days\"\n    },\n    {\n      \"name\": \"conversion_rate\",\n      \"dtype\": \"float64\",\n      \"description\": \"Conversion rate\"\n    },\n    {\n      \"name\": \"avg_rating\",\n      \"dtype\": \"float64\",\n      \"description\": \"Average rating\"\n    }\n  ],\n  \"source\": {\n    \"table_name\": \"product_interactions\",\n    \"catalog\": \"iceberg\",\n    \"schema\": \"gold\"\n  },\n  \"ttl_seconds\": 604800,\n  \"description\": \"Product interaction features\",\n  \"tags\": {\n    \"team\": \"ml-platform\"\n  },\n  \"online\": false\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/feast/features",
          "host": ["{{baseUrl}}"],
          "path": ["feast", "features"]
        }
      }
    },
    {
      "name": "4. List All Feature Views",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{baseUrl}}/feast/features",
          "host": ["{{baseUrl}}"],
          "path": ["feast", "features"]
        }
      }
    },
    {
      "name": "5. Create Feature Service",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"name\": \"recommendation_service\",\n  \"feature_views\": [\n    \"customer_behavior_features\",\n    \"product_features\"\n  ],\n  \"description\": \"Feature service for product recommendations\",\n  \"tags\": {\n    \"model\": \"recommender_v1\"\n  }\n}"
        },
        "url": {
          "raw": "{{baseUrl}}/feast/features/service",
          "host": ["{{baseUrl}}"],
          "path": ["feast", "features", "service"]
        }
      }
    }
  ]
}
```

---

## Demo Presentation Flow

### For Client Meeting (15 minutes)

**Slide 1: Introduction (2 min)**

- Show architecture diagram
- Explain Iceberg → Feast → MLOps pipeline

**Slide 2: Status Check (1 min)**

```bash
curl http://localhost:8000/feast/status | jq
```

**Slide 3: Create Customer Features (3 min)**

- Explain the business use case (churn prediction)
- Show POST request creating customer_behavior_features
- Highlight: Direct Iceberg gold layer access, no data duplication

**Slide 4: Create Support Features (2 min)**

- Show second feature view creation
- Explain TTL and feature freshness

**Slide 5: List Features (2 min)**

```bash
curl http://localhost:8000/feast/features | jq
```

- Show all registered features
- Explain metadata (types, descriptions, tags)

**Slide 6: Create Feature Service (2 min)**

- Show logical grouping of feature views
- Explain how ML models consume features

**Slide 7: Final Status (1 min)**

```bash
curl http://localhost:8000/feast/status | jq
```

- Show updated counts

**Slide 8: Next Steps (2 min)**

- Connect to ML training pipeline
- Model serving with features
- Production deployment

---

## Key Demo Talking Points

### Technical Highlights

✅ **Zero Data Duplication** - Feast reads directly from Iceberg S3 Parquet files  
✅ **Schema Evolution** - Iceberg tables evolve, Feast adapts automatically  
✅ **Metadata Rich** - Features have descriptions, types, tags for discoverability  
✅ **TTL Management** - Feature freshness controlled at view level  
✅ **Multi-Entity Support** - Customer, product, account-level features  
✅ **Feature Services** - Logical grouping for ML model consumption

### Business Value

💰 **Cost Reduction** - No duplicate storage, single source of truth  
⚡ **Faster Time to Market** - Reusable features across models  
🔒 **Data Governance** - Centralized feature catalog with metadata  
📊 **Feature Discovery** - Teams can find and reuse existing features  
🎯 **Consistency** - Same features for training and serving

---

## Troubleshooting

### Issue: "Table not found in Iceberg"

**Solution:** Ensure table exists in Iceberg gold layer first

```sql
-- Check in Trino
SHOW TABLES IN iceberg.gold;
```

### Issue: "Entity not found"

**Solution:** Entities are created automatically on first use. Ensure entity name matches join key in source table.

### Issue: "Connection refused"

**Solution:** Verify port forwarding is active

```bash
kubectl port-forward -n asgard svc/asgard-app 8000:80
```

---

## Summary

This demo guide provides **complete, ready-to-use examples** for demonstrating Feast Feature Store integration with Iceberg. All API endpoints are covered with:

- ✅ Realistic business use cases
- ✅ Complete request/response examples
- ✅ cURL commands for live demos
- ✅ Python client for automation
- ✅ Postman collection for GUI testing
- ✅ Presentation flow for client meetings

**Status: Production Ready** 🚀

---

**Last Updated:** November 4, 2025  
**Author:** Asgard Platform Team  
**Contact:** For questions, check `/feast/status` or review pod logs
