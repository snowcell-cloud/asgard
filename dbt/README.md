# Asgard Data Products - dbt Project

[![dbt CI/CD Pipeline](https://github.com/snowcell-cloud/asgard-dev/actions/workflows/dbt-ci-cd.yml/badge.svg)](https://github.com/snowcell-cloud/asgard-dev/actions/workflows/dbt-ci-cd.yml)

A modern data transformation pipeline built with dbt, creating curated data products on top of Trino/Nessie/Iceberg infrastructure.

## 🎯 Overview

This dbt project transforms raw silver layer data into business-ready data products stored in the gold layer. Each data product is designed for specific business use cases with built-in data quality, governance, and documentation.

### Data Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Silver Layer  │───▶│   dbt Models    │───▶│   Gold Layer    │
│   (Raw Data)    │    │ (Transformations)│    │ (Data Products) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                        │                        │
       │                        │                        │
    Airbyte               dbt Transformations        Business Apps
   Raw Sources            Quality & Governance        Analytics & ML
```

## 🏗️ Project Structure

```
dbt/
├── dbt_project.yml              # Project configuration
├── profiles_template.yml        # Connection profiles template
├── packages.yml                 # dbt package dependencies
├── models/
│   ├── sources.yml             # Source data definitions
│   ├── schema_clean.yml        # Model documentation & tests
│   ├── staging/                # Source data standardization
│   │   ├── stg_customers_clean.sql
│   │   ├── stg_orders.sql
│   │   └── stg_products_clean.sql
│   ├── intermediate/           # Business logic transformations
│   │   ├── int_customer_360.sql
│   │   └── int_product_performance.sql
│   ├── data_products/          # Final curated data products
│   │   ├── dp_customer_360_clean.sql
│   │   └── dp_product_performance_clean.sql
│   └── metrics/                # Aggregated metrics
├── tests/                      # Custom data quality tests
│   ├── assert_data_product_freshness.sql
│   ├── assert_customer_value_score_logic.sql
│   └── assert_product_performance_logic.sql
├── macros/                     # Reusable SQL functions
│   └── data_product_macros.sql
├── analyses/                   # Ad-hoc analytical queries
├── seeds/                      # Static data files
└── snapshots/                  # SCD Type 2 history tracking
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Access to Trino cluster
- dbt-trino adapter
- AWS credentials (for S3 access)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/snowcell-cloud/asgard-dev.git
   cd asgard-dev/dbt
   ```

2. **Install dbt and dependencies:**
   ```bash
   pip install dbt-trino==1.6.* dbt-utils dbt-expectations
   dbt deps
   ```

3. **Configure profiles:**
   ```bash
   cp profiles_template.yml ~/.dbt/profiles.yml
   # Edit with your Trino connection details
   ```

4. **Test connection:**
   ```bash
   dbt debug
   ```

### Running the Project

```bash
# Install dependencies
dbt deps

# Run all models
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve
```

## 📊 Data Products

### 1. Customer 360 (`dp_customer_360_clean`)

**Purpose:** Comprehensive customer view with behavioral insights and segmentation.

**Key Features:**
- Customer lifecycle tracking (prospects → active → at-risk → churned)
- Value tier classification (high/medium/low/no value)
- Engagement scoring based on purchase recency
- Customer value score (0-100 scale)

**Business Use Cases:**
- Marketing campaign targeting
- Customer success interventions
- Sales prioritization
- Churn prevention

**Schema:**
```sql
customer_id              -- Unique customer identifier
customer_name            -- Full customer name
email                    -- Customer email address
customer_segment         -- Lifecycle segment
value_tier              -- Value classification
customer_value_score    -- Composite score (0-100)
engagement_level        -- Engagement classification
total_orders            -- Number of orders placed
total_spent             -- Total revenue from customer
avg_order_value         -- Average order value
```

### 2. Product Performance (`dp_product_performance_clean`)

**Purpose:** Product analytics with sales performance and lifecycle tracking.

**Key Features:**
- Sales volume and revenue tier classification
- Product lifecycle stage tracking
- Performance scoring (0-100 scale)
- Revenue per order/customer metrics

**Business Use Cases:**
- Product portfolio analysis
- Inventory optimization
- Pricing strategy
- Product lifecycle management

**Schema:**
```sql
product_id                      -- Unique product identifier
product_name                    -- Product name
product_category               -- Product category
sales_volume_tier             -- Volume classification
revenue_tier                  -- Revenue classification
product_performance_score     -- Composite score (0-100)
product_lifecycle_stage       -- Lifecycle stage
total_revenue                 -- Total revenue generated
revenue_per_order            -- Revenue efficiency metric
```

## 🔍 Data Quality & Testing

### Built-in Tests

- **Uniqueness:** Primary key constraints on all data products
- **Completeness:** Non-null checks on critical fields
- **Validity:** Range checks on scores and metrics
- **Consistency:** Business logic validation
- **Freshness:** Data recency monitoring

### Custom Tests

- Data product freshness (< 2 days old)
- Score range validation (0-100)
- Business logic consistency
- Cross-model referential integrity

### Running Tests

```bash
# Run all tests
dbt test

# Run tests for specific models
dbt test --select dp_customer_360_clean

# Run only freshness tests
dbt test --select test_type:freshness
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The project includes a comprehensive CI/CD pipeline with:

- **Pull Request Validation:**
  - SQL linting with SQLFluff
  - dbt compilation checks
  - Dry run testing
  - Documentation generation

- **Staging Deployment:**
  - Automated deployment to staging environment
  - Full test suite execution
  - Artifact preservation

- **Production Deployment:**
  - Backup creation before deployment
  - Production model execution
  - Documentation deployment to S3
  - Success notifications

- **Scheduled Runs:**
  - Daily automated refresh at 6 AM UTC
  - Data quality monitoring
  - Failure alerts

### Environment Configuration

Set the following secrets in GitHub:

```bash
TRINO_HOST=trino.data-platform.svc.cluster.local
TRINO_PORT=8080
TRINO_CATALOG=iceberg
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=your_aws_region
DBT_DOCS_BUCKET=your_s3_bucket
```

## 🛠️ Development Workflow

### Adding New Data Products

1. **Create intermediate model** (if needed):
   ```sql
   -- models/intermediate/int_new_product.sql
   {{ config(materialized='view') }}
   
   SELECT 
     -- your transformation logic
   FROM {{ ref('stg_source_table') }}
   ```

2. **Create data product model:**
   ```sql
   -- models/data_products/dp_new_product.sql
   {{ config(
     materialized='table',
     tags=['data_product', 'your_tag']
   ) }}
   
   SELECT 
     *,
     {{ generate_data_product_metadata('dp_new_product', 'CUSTOM') }}
   FROM {{ ref('int_new_product') }}
   ```

3. **Add documentation and tests:**
   ```yaml
   # models/schema_clean.yml
   - name: dp_new_product
     description: "Your data product description"
     columns:
       - name: primary_key
         tests:
           - not_null
           - unique
   ```

4. **Test your changes:**
   ```bash
   dbt run --select dp_new_product
   dbt test --select dp_new_product
   ```

### Best Practices

- **Naming Conventions:**
  - `stg_` for staging models
  - `int_` for intermediate models
  - `dp_` for data products
  - `_clean` suffix for cleaned/production versions

- **Model Organization:**
  - One model per file
  - Clear dependencies (`ref()` functions)
  - Consistent column naming
  - Comprehensive documentation

- **Performance:**
  - Use appropriate materializations
  - Leverage Iceberg table properties
  - Consider partitioning for large datasets
  - Monitor query performance

## 📈 Monitoring & Observability

### Key Metrics

- Model execution times
- Test failure rates
- Data freshness scores
- Row count trends
- Data quality scores

### Alerting

- Failed model runs
- Test failures
- Data freshness violations
- Significant row count changes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-data-product`
3. Make your changes following the development workflow
4. Run tests: `dbt test`
5. Submit a pull request

### Code Review Checklist

- [ ] Model follows naming conventions
- [ ] Documentation is complete
- [ ] Tests are included
- [ ] Performance is acceptable
- [ ] No sensitive data exposure

## 📚 Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [dbt-trino Adapter](https://github.com/starburstdata/dbt-trino)
- [Trino Documentation](https://trino.io/docs/)
- [Iceberg Documentation](https://iceberg.apache.org/docs/)

## 🆘 Support

For questions, issues, or feature requests:

1. Check existing [GitHub Issues](https://github.com/snowcell-cloud/asgard-dev/issues)
2. Create a new issue with detailed description
3. Contact the data platform team: `data-platform-team@company.com`

---

**Last Updated:** October 2025  
**Version:** 1.0.0  
**Maintainer:** Data Platform Team