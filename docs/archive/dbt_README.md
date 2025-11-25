# DBT Transformations API

This module provides a comprehensive API for SQL-driven data transformations from silver layer to gold layer using dbt, Trino, and Iceberg tables.

## 🚀 Features

- **SQL-Driven Transformations**: Submit SQL queries via API to create dynamic dbt models
- **Silver-to-Gold Pipeline**: Automated transformations from raw silver data to curated gold layer
- **Multiple Materializations**: Support for table, view, and incremental materializations
- **Security**: Built-in SQL injection protection and query validation
- **S3 Integration**: Native support for S3-based data lakes with Iceberg format
- **Trino Integration**: Leverages Trino for distributed query processing
- **API-Triggered**: No cron jobs - transformations run only when triggered via API

## 📋 Prerequisites

- Trino cluster with Iceberg connector
- Nessie catalog (optional but recommended)
- S3 bucket with silver and gold layer data
- dbt Core installed
- Python 3.8+ with FastAPI

## 🛠️ Configuration

1. Copy the environment configuration:

```bash
cp .env.example .env
```

2. Update the configuration with your values:

```bash
# Key settings to update
TRINO_HOST=your-trino-host
TRINO_PORT=8080
TRINO_CATALOG=iceberg
SILVER_SCHEMA=silver
GOLD_SCHEMA=gold
S3_BUCKET=your-data-lake-bucket
```

3. Ensure your dbt `profiles.yml` is configured for Trino:

```yaml
asgard:
  target: prod
  outputs:
    prod:
      type: trino
      method: none
      host: "{{ env_var('TRINO_HOST') }}"
      port: "{{ env_var('TRINO_PORT') | int }}"
      user: "{{ env_var('TRINO_USER') }}"
      catalog: "{{ env_var('TRINO_CATALOG') }}"
      schema: "{{ env_var('GOLD_SCHEMA') }}"
```

## 🚀 Quick Start

1. Start the API server:

```bash
cd /home/hac/downloads/code/asgard-dev
python -m app.main
```

2. Test the API:

```bash
./test-dbt-transformations-api.sh
```

3. Access the interactive documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📊 API Endpoints

### Core Transformation Operations

- `POST /api/v1/dbt-transformations/transform` - Create and execute transformation
- `GET /api/v1/dbt-transformations/transformations` - List all transformations
- `GET /api/v1/dbt-transformations/transformations/{id}` - Get transformation details
- `DELETE /api/v1/dbt-transformations/transformations/{id}` - Delete transformation

### Discovery and Validation

- `GET /api/v1/dbt-transformations/sources/silver` - List silver layer sources
- `GET /api/v1/dbt-transformations/tables/gold` - List gold layer tables
- `POST /api/v1/dbt-transformations/validate-sql` - Validate SQL query
- `GET /api/v1/dbt-transformations/examples/sql` - Get example queries

### Utility

- `GET /api/v1/dbt-transformations/health` - Health check

## 💡 Usage Examples

### 1. Customer Aggregation

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_monthly_summary",
    "sql_query": "SELECT customer_id, DATE_TRUNC('\''month'\'', transaction_date) as month, COUNT(*) as transaction_count, SUM(amount) as total_amount FROM silver.transaction_data WHERE transaction_date >= CURRENT_DATE - INTERVAL '\''6'\'' MONTH GROUP BY customer_id, DATE_TRUNC('\''month'\'', transaction_date)",
    "description": "Monthly customer transaction summary",
    "materialization": "table",
    "tags": ["customer", "monthly"],
    "owner": "data-team"
  }'
```

### 2. Incremental Daily Processing

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_transaction_summary",
    "sql_query": "SELECT transaction_date, COUNT(*) as total_transactions, SUM(amount) as total_amount FROM silver.transaction_data GROUP BY transaction_date",
    "materialization": "incremental",
    "incremental_strategy": "merge",
    "unique_key": ["transaction_date"]
  }'
```

### 3. Validate SQL Before Transformation

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/validate-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT customer_id, COUNT(*) FROM silver.transaction_data GROUP BY customer_id"
  }'
```

## 🔒 Security Features

- **SQL Injection Protection**: Automatic detection and blocking of dangerous SQL operations
- **Query Validation**: Comprehensive validation before execution
- **Read-Only Operations**: Only SELECT statements allowed in transformations
- **Input Sanitization**: All inputs validated with Pydantic models

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Silver Layer  │───▶│  DBT Transform  │───▶│   Gold Layer    │
│  (Raw S3 Data)  │    │   (API Driven)  │    │ (Curated Data)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
    Iceberg Tables         Dynamic Models           Iceberg Tables
     Trino Access           dbt Execution            Trino Access
```

## 🔧 Advanced Configuration

### Custom dbt Models Directory

The service automatically creates model files in `{DBT_PROJECT_DIR}/models/gold/`. Ensure this directory exists and is writable.

### Trino Connection Tuning

For production environments, consider:

- Connection pooling
- Query timeout settings
- Resource management
- Authentication setup

### S3 Optimization

- Use appropriate S3 storage classes
- Configure lifecycle policies
- Implement proper partitioning strategies
- Consider S3 Transfer Acceleration

## 📈 Monitoring and Observability

The API provides comprehensive logging and metrics:

- Transformation execution times
- Query performance statistics
- Error tracking and reporting
- Table size and row count metrics

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Basic functionality test
./test-dbt-transformations-api.sh

# Manual testing with curl
curl -X GET "http://localhost:8000/api/v1/dbt-transformations/health"
```

## 🤝 Integration

### With Data Products API

The dbt transformations seamlessly integrate with the Data Products API, allowing you to:

1. Transform data with dbt
2. Register as data products
3. Manage lifecycle and access

### With Existing Workflows

- **Airflow**: Trigger transformations from DAGs
- **GitHub Actions**: Automated testing and deployment
- **Monitoring**: Integrate with your observability stack

## 📚 Best Practices

1. **Naming Conventions**: Use descriptive, consistent names for transformations
2. **Documentation**: Always provide descriptions for complex transformations
3. **Tags**: Use tags for organization and discovery
4. **Incremental Models**: Use for large datasets that change frequently
5. **Testing**: Validate queries before creating transformations
6. **Monitoring**: Regularly check transformation status and performance

## 🆘 Troubleshooting

### Common Issues

1. **Trino Connection Errors**

   - Check TRINO_HOST and TRINO_PORT settings
   - Verify network connectivity
   - Confirm Trino cluster is running

2. **dbt Execution Failures**

   - Check DBT_PROJECT_DIR path
   - Verify profiles.yml configuration
   - Ensure proper permissions

3. **S3 Access Issues**
   - Verify AWS credentials
   - Check S3 bucket permissions
   - Confirm Iceberg catalog configuration

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=debug
python -m app.main
```

## 📄 License

This project is part of the Asgard Data Platform and follows the same licensing terms.
