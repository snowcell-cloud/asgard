# 🚀 Production Testing Guide for DBT Transformations API

This guide provides comprehensive instructions for testing the DBT Transformations API in your production environment with real Trino/Nessie/Iceberg infrastructure.

## 📋 Pre-Production Checklist

### 1. Infrastructure Requirements

- [ ] Trino cluster running and accessible
- [ ] Nessie catalog deployed and configured
- [ ] S3 buckets set up for silver and gold layers
- [ ] Iceberg tables configured in Trino
- [ ] Network connectivity between API and Trino
- [ ] Proper IAM/security permissions configured

### 2. Application Requirements

- [ ] DBT Core installed and configured
- [ ] Python 3.8+ with required packages
- [ ] FastAPI application deployed
- [ ] Environment variables configured
- [ ] ConfigMaps and Secrets created (for Kubernetes)

### 3. Data Requirements

- [ ] Silver layer tables exist with sample data
- [ ] Table schemas are documented
- [ ] Data quality validated
- [ ] Access permissions verified

## 🛠️ Step-by-Step Testing Process

### Step 1: Environment Validation

```bash
# Run comprehensive environment validation
./validate-production-env.sh
```

**Expected Output:**

- All system checks pass
- dbt configuration validated
- Trino connectivity confirmed
- Required directories exist

### Step 2: Basic API Testing

```bash
# Start the application (if not already running)
python -m app.main

# In another terminal, run basic tests
./production-test-dbt-api.sh
```

**Key Tests Performed:**

- Health checks
- SQL validation
- Silver layer discovery
- Basic transformation creation
- Security validation
- Error handling

### Step 3: Real Infrastructure Integration

```bash
# Test against actual Trino/Nessie infrastructure
export TRINO_HOST=your-trino-host
export TRINO_PORT=8080
export API_BASE_URL=http://your-api-host:8000

./test-production-integration.sh
```

**Integration Tests:**

- Real silver layer data discovery
- Actual transformation execution
- Gold layer table creation
- Performance validation
- End-to-end workflows

### Step 4: Load and Performance Testing

```bash
# Run concurrent transformations
for i in {1..5}; do
  curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"load_test_${i}_$(date +%s)\",
      \"sql_query\": \"SELECT COUNT(*) as row_count FROM silver.your_table\",
      \"materialization\": \"table\"
    }" &
done
wait
```

## 🔧 Configuration Examples

### Environment Variables

```bash
# Core Trino Configuration
export TRINO_HOST=trino.your-domain.com
export TRINO_PORT=8080
export TRINO_USER=dbt_user
export TRINO_CATALOG=iceberg

# Schema Configuration
export SILVER_SCHEMA=silver
export GOLD_SCHEMA=gold

# dbt Configuration
export DBT_PROJECT_DIR=/path/to/your/dbt/project
export DBT_PROFILES_DIR=/path/to/dbt/profiles

# S3 Configuration (if needed)
export S3_BUCKET=your-data-lake-bucket
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Nessie Configuration
export NESSIE_URI=http://nessie.your-domain.com:19120/api/v1
export NESSIE_REF=main
```

### dbt profiles.yml Example

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
      http_scheme: http
      session_properties:
        iceberg.delete_mode: merge-on-read
        iceberg.merge_mode: merge-on-read
```

## 🧪 Sample Test Cases

### 1. Basic Aggregation Test

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer_summary_test",
    "sql_query": "SELECT customer_id, COUNT(*) as transaction_count, SUM(amount) as total_amount FROM silver.transactions GROUP BY customer_id LIMIT 1000",
    "description": "Customer transaction summary test",
    "materialization": "table",
    "tags": ["test", "customer"]
  }'
```

### 2. Date-Based Transformation Test

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_metrics_test",
    "sql_query": "SELECT DATE(transaction_date) as date, COUNT(*) as daily_transactions, SUM(amount) as daily_revenue FROM silver.transactions WHERE transaction_date >= CURRENT_DATE - INTERVAL '\''30'\'' DAY GROUP BY DATE(transaction_date)",
    "materialization": "table",
    "tags": ["test", "daily", "metrics"]
  }'
```

### 3. Incremental Model Test

```bash
curl -X POST "http://localhost:8000/api/v1/dbt-transformations/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "incremental_test",
    "sql_query": "SELECT transaction_date, COUNT(*) as count, SUM(amount) as total FROM silver.transactions GROUP BY transaction_date",
    "materialization": "incremental",
    "incremental_strategy": "merge",
    "unique_key": ["transaction_date"],
    "tags": ["test", "incremental"]
  }'
```

## 📊 Performance Benchmarks

### Expected Response Times

- Health check: < 100ms
- SQL validation: < 200ms
- Silver layer discovery: < 500ms
- Simple transformation: < 30 seconds
- Complex transformation: < 5 minutes

### Resource Usage

- Memory: 512MB - 2GB (depending on data size)
- CPU: 1-2 cores for typical workloads
- Network: Depends on data transfer volume

## 🔍 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Trino Connection Failures

**Symptoms:** Connection timeout, authentication errors
**Solutions:**

- Verify TRINO_HOST and TRINO_PORT
- Check network connectivity: `telnet $TRINO_HOST $TRINO_PORT`
- Validate credentials and permissions
- Check Trino cluster status

#### 2. dbt Execution Failures

**Symptoms:** dbt run command fails, model compilation errors
**Solutions:**

- Verify dbt_project.yml syntax
- Check profiles.yml configuration
- Ensure proper file permissions
- Validate SQL syntax in transformations

#### 3. S3 Access Issues

**Symptoms:** Table not found, access denied errors
**Solutions:**

- Verify AWS credentials
- Check S3 bucket permissions
- Confirm Iceberg catalog configuration
- Test direct S3 access

#### 4. Memory/Performance Issues

**Symptoms:** Slow transformations, out of memory errors
**Solutions:**

- Increase container memory limits
- Optimize SQL queries
- Add LIMIT clauses for testing
- Use incremental models for large datasets

### Debug Commands

```bash
# Check API logs
kubectl logs deployment/asgard-data-platform-api -n asgard

# Test Trino connectivity
curl -v http://$TRINO_HOST:$TRINO_PORT/v1/info

# Validate dbt configuration
cd $DBT_PROJECT_DIR && dbt debug --profiles-dir .

# Check silver layer tables directly
curl -s "http://localhost:8000/api/v1/dbt-transformations/sources/silver" | jq '.'
```

## 📈 Monitoring and Observability

### Key Metrics to Monitor

- API response times
- Transformation success/failure rates
- Resource utilization (CPU, memory)
- Data processing volumes
- Error rates and types

### Log Analysis

Monitor logs for:

- HTTP error codes (4xx, 5xx)
- dbt execution failures
- SQL parsing errors
- Connection timeouts
- Resource exhaustion

### Alerts to Configure

- API health check failures
- Transformation failure rate > 10%
- Response time > 30 seconds
- Memory usage > 80%
- Disk space low in dbt project directory

## 🚀 Production Deployment

### Kubernetes Deployment

```bash
# Deploy to production cluster
./deploy-production-enhanced.sh

# Verify deployment
kubectl get pods -n asgard -l app=asgard-data-platform-api

# Check service status
kubectl get service asgard-data-platform-api -n asgard
```

### Configuration Management

- Use Kubernetes ConfigMaps for application code
- Store sensitive data in Secrets
- Implement proper RBAC
- Configure resource limits and requests

## ✅ Production Readiness Criteria

Before declaring production ready, ensure:

- [ ] All test suites pass (>95% success rate)
- [ ] Performance benchmarks met
- [ ] Security validation completed
- [ ] Error handling verified
- [ ] Monitoring and alerting configured
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Backup and recovery procedures in place

## 📚 Additional Resources

- [DBT Documentation](https://docs.getdbt.com/)
- [Trino Documentation](https://trino.io/docs/)
- [Iceberg Documentation](https://iceberg.apache.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

## 🆘 Support and Escalation

For production issues:

1. Check application logs and metrics
2. Run diagnostic scripts
3. Review recent configuration changes
4. Escalate to platform team if needed
5. Document issues for future reference

Remember: Always test in a staging environment that mirrors production before deploying changes!
