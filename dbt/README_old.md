# Asgard Data Products

This directory contains the dbt project for creating curated, governed, and reusable data products on top of your Trino/Nessie/Iceberg infrastructure.

## Overview

Data products are curated datasets that transform raw silver layer data into business-ready analytical assets. Each data product includes:

- **Metadata** (owner, consumers, update frequency)
- **Data lineage** tracking from source to consumption
- **Quality checks** and validation tests
- **API access** for programmatic consumption
- **Automated refresh** capabilities

## Project Structure

```
dbt/
├── dbt_project.yml          # Project configuration
├── profiles.yml             # Trino connection settings
├── models/
│   ├── staging/             # Source data standardization
│   ├── intermediate/        # Business logic transformations
│   ├── data_products/       # Final curated data products
│   └── metrics/             # Aggregated metrics
├── tests/                   # Data quality tests
├── macros/                  # Reusable SQL functions
└── README.md               # This file
```

## Available Data Products

### 1. Customer 360 (`dp_customer_360`)

- **Type**: CUSTOMER_360
- **Description**: Comprehensive customer view with transaction history and segmentation
- **Updates**: Daily
- **Consumers**: Marketing, Customer Success, Analytics teams

### 2. Product Performance (`dp_product_performance`)

- **Type**: PRODUCT_PERFORMANCE
- **Description**: Product sales metrics and performance analytics
- **Updates**: Daily
- **Consumers**: Product, Sales, Analytics teams

### 3. Revenue Analytics (`dp_revenue_analytics`)

- **Type**: REVENUE_ANALYTICS
- **Description**: Monthly revenue trends and growth analytics
- **Updates**: Monthly
- **Consumers**: Finance, Executive, Analytics teams

## Setup and Configuration

### Prerequisites

- Trino cluster running with Nessie catalog
- S3/Iceberg warehouse configured
- dbt-trino adapter installed
- Python dependencies: `pip install dbt-trino`

### Configuration

1. **Update profiles.yml** with your Trino connection details:

```yaml
asgard_data_products:
  target: dev
  outputs:
    dev:
      type: trino
      host: trino.data-platform.svc.cluster.local
      port: 8080
      catalog: nessie
      schema: gold
```

2. **Configure project variables** in `dbt_project.yml`:

```yaml
vars:
  iceberg_warehouse: "s3a://airbytedestination1/iceberg/"
  nessie_uri: "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
  silver_schema: "silver"
  gold_schema: "gold"
```

## Running Data Products

### Using dbt directly:

```bash
# Run all data products
dbt run

# Run specific data product
dbt run --select dp_customer_360

# Test data quality
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

### Using the API:

```bash
# Create a new data product
curl -X POST "http://localhost:8000/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Data Product",
    "description": "Custom analytics dataset",
    "data_product_type": "CUSTOM",
    "source_query": "SELECT * FROM nessie.silver.my_table",
    "owner": "my-team"
  }'

# Run/refresh a data product
curl -X POST "http://localhost:8000/api/v1/data-products/{id}/run"

# Query data from a data product
curl "http://localhost:8000/api/v1/data-products/{id}/query?limit=100"
```

## Best Practices

1. **Naming Conventions**

   - Use descriptive names: `dp_customer_churn_prediction`
   - Include business context: `dp_sales_performance_by_region`

2. **Documentation**

   - Add clear descriptions to all models
   - Document column meanings and calculations
   - Include business logic rationale

3. **Testing**

   - Test primary key uniqueness
   - Validate business rules
   - Check data freshness
   - Monitor data quality metrics

4. **Performance**
   - Use Iceberg table properties for optimization
   - Implement incremental models for large datasets
   - Consider partitioning strategies

## Integration with Existing Infrastructure

This dbt project integrates seamlessly with your existing Asgard platform:

- **Source Data**: Reads from silver layer tables in S3/Iceberg
- **Transformations**: Uses Trino's SQL capabilities for complex analytics
- **Storage**: Writes to Iceberg tables for ACID compliance and time travel
- **Catalog**: Managed through Nessie for branch/merge workflows
- **API**: Exposed through FastAPI endpoints for programmatic access
- **Orchestration**: Can be triggered via Spark/K8s jobs or API calls

## Monitoring and Observability

Data products include built-in observability:

- **Lineage tracking**: Source → Transformation → Consumer mapping
- **Quality metrics**: Null rates, duplicate counts, freshness
- **Usage analytics**: Query patterns, consumer adoption
- **Performance monitoring**: Execution times, resource usage
- **Data drift detection**: Schema and distribution changes

## Extending the Framework

To add new data product types:

1. Create new models in `models/data_products/`
2. Add corresponding schemas in `models/data_products/schema.yml`
3. Update API schemas in `app/data_products/schemas.py`

Example new data product:

```sql
-- models/data_products/dp_customer_churn.sql
{{
  config(
    materialized='table',
    description='Customer churn prediction model results'
  )
}}

SELECT
    customer_id,
    churn_probability,
    risk_factors,
    recommended_actions,
    model_version,
    CURRENT_TIMESTAMP as data_product_updated_at
FROM {{ ref('int_customer_churn_features') }}
WHERE churn_probability > 0.3
```
