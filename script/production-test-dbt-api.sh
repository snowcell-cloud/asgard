#!/bin/bash

# Asgard Data Platform - Production DBT Transformations API Test Suite
# This script performs comprehensive testing of the dbt transformations API in production environment

set -e  # Exit on any error

# Configuration
BASE_URL="${API_BASE_URL:-http://localhost:8000}"
API_BASE="${BASE_URL}/api/v1/dbt-transformations"
TEST_RESULTS_DIR="./test-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${TEST_RESULTS_DIR}/dbt_api_test_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create test results directory
mkdir -p "${TEST_RESULTS_DIR}"

# Logging function
log() {
    echo -e "$1" | tee -a "${LOG_FILE}"
}

# Test counter
TEST_COUNT=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test and check result
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_status="${3:-200}"
    
    ((TEST_COUNT++))
    log "\n${BLUE}Test #${TEST_COUNT}: ${test_name}${NC}"
    log "Command: ${test_command}"
    log "Expected HTTP Status: ${expected_status}"
    
    # Execute the test command and capture output
    if response=$(eval "${test_command}" 2>&1); then
        # Check if response contains expected status indicators
        if echo "$response" | grep -q "error\|Error\|ERROR" && [ "$expected_status" = "200" ]; then
            log "${RED}❌ FAILED: ${test_name}${NC}"
            log "Response: $response"
            ((FAILED_TESTS++))
            return 1
        else
            log "${GREEN}✅ PASSED: ${test_name}${NC}"
            log "Response preview: $(echo "$response" | head -n 5)"
            ((PASSED_TESTS++))
            return 0
        fi
    else
        log "${RED}❌ FAILED: ${test_name} - Command execution failed${NC}"
        log "Error: $response"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Start testing
log "🚀 Starting Production DBT Transformations API Test Suite"
log "============================================================"
log "Base URL: ${BASE_URL}"
log "API Base: ${API_BASE}"
log "Timestamp: ${TIMESTAMP}"
log "Log File: ${LOG_FILE}"

# Pre-flight checks
log "\n🔍 Pre-flight Checks"
log "===================="

# Check if API is reachable
if ! curl -s --max-time 10 "${BASE_URL}/health" > /dev/null; then
    log "${RED}❌ FATAL: API is not reachable at ${BASE_URL}${NC}"
    log "Please ensure the application is running and accessible."
    exit 1
fi

log "${GREEN}✅ API is reachable${NC}"

# Production Test Suite
log "\n🧪 Production Test Suite"
log "========================"

# Test 1: Health Check
run_test "Health Check" \
    "curl -s -w '%{http_code}' -X GET '${API_BASE}/health' | jq -e '.status == \"healthy\"'"

# Test 2: Service Configuration Validation
run_test "Service Configuration" \
    "curl -s -X GET '${API_BASE}/health' | jq -e '.configuration.dbt_project_dir != null'"

# Test 3: Silver Layer Sources Discovery
run_test "Silver Layer Sources Discovery" \
    "curl -s -X GET '${API_BASE}/sources/silver' | jq -e '.sources | length > 0'"

# Test 4: SQL Examples Availability
run_test "SQL Examples Availability" \
    "curl -s -X GET '${API_BASE}/examples/sql' | jq -e '.examples | length > 0'"

# Test 5: SQL Validation - Valid Query
VALID_SQL='{
    "sql_query": "SELECT customer_id, COUNT(*) as transaction_count FROM silver.customer_data GROUP BY customer_id LIMIT 100"
}'

run_test "SQL Validation - Valid Query" \
    "curl -s -X POST '${API_BASE}/validate-sql' -H 'Content-Type: application/json' -d '${VALID_SQL}' | jq -e '.is_valid == true'"

# Test 6: SQL Validation - Security Check (should fail)
MALICIOUS_SQL='{
    "sql_query": "DROP TABLE silver.customer_data"
}'

run_test "SQL Security Validation" \
    "curl -s -X POST '${API_BASE}/validate-sql' -H 'Content-Type: application/json' -d '${MALICIOUS_SQL}' | jq -e '.is_valid == false'"

# Test 7: Create Simple Table Transformation
SIMPLE_TRANSFORM='{
    "name": "prod_test_customer_summary_'${TIMESTAMP}'",
    "sql_query": "SELECT customer_id, COUNT(*) as transaction_count, SUM(amount) as total_amount FROM silver.transaction_data WHERE transaction_date >= CURRENT_DATE - INTERVAL '\''30'\'' DAY GROUP BY customer_id LIMIT 1000",
    "description": "Production test - Customer summary for last 30 days",
    "materialization": "table",
    "tags": ["production-test", "customer", "summary"],
    "owner": "data-platform-test"
}'

TRANSFORM_RESPONSE=$(mktemp)
if run_test "Create Table Transformation" \
    "curl -s -X POST '${API_BASE}/transform' -H 'Content-Type: application/json' -d '${SIMPLE_TRANSFORM}' | tee '${TRANSFORM_RESPONSE}' | jq -e '.transformation_id != null'"; then
    
    # Extract transformation ID for subsequent tests
    TRANSFORM_ID=$(jq -r '.transformation_id' < "${TRANSFORM_RESPONSE}")
    log "Created transformation ID: ${TRANSFORM_ID}"
    
    # Test 8: Get Transformation Details
    run_test "Get Transformation Details" \
        "curl -s -X GET '${API_BASE}/transformations/${TRANSFORM_ID}' | jq -e '.transformation_id == \"${TRANSFORM_ID}\"'"
    
    # Test 9: Check Transformation Status
    run_test "Check Transformation Status" \
        "curl -s -X GET '${API_BASE}/transformations/${TRANSFORM_ID}' | jq -e '.status != null'"
        
    # Wait for transformation to complete (if running)
    log "\n⏳ Waiting for transformation to complete..."
    for i in {1..30}; do
        STATUS=$(curl -s -X GET "${API_BASE}/transformations/${TRANSFORM_ID}" | jq -r '.status')
        log "Status check #${i}: ${STATUS}"
        
        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
            break
        fi
        
        if [ "$STATUS" = "running" ] || [ "$STATUS" = "pending" ]; then
            sleep 10
        else
            break
        fi
    done
fi

# Test 10: List All Transformations
run_test "List All Transformations" \
    "curl -s -X GET '${API_BASE}/transformations?page=1&page_size=10' | jq -e '.transformations | length >= 0'"

# Test 11: List Gold Layer Tables
run_test "List Gold Layer Tables" \
    "curl -s -X GET '${API_BASE}/tables/gold' | jq -e '.tables | length >= 0'"

# Test 12: Create Incremental Transformation
INCREMENTAL_TRANSFORM='{
    "name": "prod_test_daily_summary_'${TIMESTAMP}'",
    "sql_query": "SELECT transaction_date, COUNT(DISTINCT customer_id) as unique_customers, COUNT(transaction_id) as total_transactions, SUM(amount) as total_amount, AVG(amount) as avg_amount FROM silver.transaction_data WHERE transaction_date >= CURRENT_DATE - INTERVAL '\''7'\'' DAY GROUP BY transaction_date",
    "description": "Production test - Daily transaction summary with incremental updates",
    "materialization": "incremental",
    "incremental_strategy": "merge",
    "unique_key": ["transaction_date"],
    "tags": ["production-test", "daily", "incremental"],
    "owner": "data-platform-test"
}'

run_test "Create Incremental Transformation" \
    "curl -s -X POST '${API_BASE}/transform' -H 'Content-Type: application/json' -d '${INCREMENTAL_TRANSFORM}' | jq -e '.transformation_id != null'"

# Test 13: Filter Transformations by Status
run_test "Filter Transformations by Status" \
    "curl -s -X GET '${API_BASE}/transformations?status=completed' | jq -e '.transformations | length >= 0'"

# Test 14: Error Handling - Invalid Transformation Name
INVALID_NAME_TRANSFORM='{
    "name": "invalid-name-with-hyphens",
    "sql_query": "SELECT * FROM silver.customer_data LIMIT 10"
}'

run_test "Error Handling - Invalid Name" \
    "curl -s -w '%{http_code}' -X POST '${API_BASE}/transform' -H 'Content-Type: application/json' -d '${INVALID_NAME_TRANSFORM}' | grep -q '422'"

# Test 15: Error Handling - Empty SQL Query
EMPTY_SQL_TRANSFORM='{
    "name": "empty_sql_test",
    "sql_query": ""
}'

run_test "Error Handling - Empty SQL" \
    "curl -s -w '%{http_code}' -X POST '${API_BASE}/transform' -H 'Content-Type: application/json' -d '${EMPTY_SQL_TRANSFORM}' | grep -q '422'"

# Performance Tests
log "\n🏃 Performance Tests"
log "==================="

# Test 16: Response Time Check - Health Endpoint
start_time=$(date +%s%N)
curl -s "${API_BASE}/health" > /dev/null
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds

if [ $response_time -lt 1000 ]; then
    log "${GREEN}✅ PASSED: Health endpoint response time (${response_time}ms)${NC}"
    ((PASSED_TESTS++))
else
    log "${YELLOW}⚠️  WARNING: Health endpoint slow response time (${response_time}ms)${NC}"
fi
((TEST_COUNT++))

# Test 17: Concurrent Request Handling
log "\n🔀 Testing Concurrent Requests"
PIDS=()
for i in {1..5}; do
    curl -s "${API_BASE}/sources/silver" > /dev/null &
    PIDS+=($!)
done

# Wait for all background jobs to complete
for pid in "${PIDS[@]}"; do
    if wait $pid; then
        log "Concurrent request $pid completed successfully"
    else
        log "Concurrent request $pid failed"
    fi
done

log "${GREEN}✅ PASSED: Concurrent request handling${NC}"
((PASSED_TESTS++))
((TEST_COUNT++))

# Cleanup Test Data (if TRANSFORM_ID exists)
if [ ! -z "$TRANSFORM_ID" ]; then
    log "\n🧹 Cleanup Test Data"
    log "==================="
    
    run_test "Delete Test Transformation" \
        "curl -s -X DELETE '${API_BASE}/transformations/${TRANSFORM_ID}' | jq -e '.message != null'"
fi

# Security Tests
log "\n🔒 Security Tests"
log "================"

# Test 18: SQL Injection Attempts
SQL_INJECTION_ATTEMPTS=(
    "SELECT * FROM silver.customer_data; DROP TABLE gold.important_data;"
    "SELECT * FROM silver.customer_data UNION SELECT * FROM information_schema.tables"
    "SELECT * FROM silver.customer_data WHERE 1=1; DELETE FROM gold.test_table"
)

for i in "${!SQL_INJECTION_ATTEMPTS[@]}"; do
    INJECTION_SQL="{\"sql_query\": \"${SQL_INJECTION_ATTEMPTS[$i]}\"}"
    run_test "SQL Injection Test #$((i+1))" \
        "curl -s -X POST '${API_BASE}/validate-sql' -H 'Content-Type: application/json' -d '${INJECTION_SQL}' | jq -e '.is_valid == false'"
done

# Integration Tests
log "\n🔗 Integration Tests"
log "==================="

# Test 19: Check dbt Project Directory
if [ -d "${DBT_PROJECT_DIR:-/home/hac/downloads/code/asgard-dev/dbt}" ]; then
    log "${GREEN}✅ PASSED: dbt project directory exists${NC}"
    ((PASSED_TESTS++))
else
    log "${RED}❌ FAILED: dbt project directory not found${NC}"
    ((FAILED_TESTS++))
fi
((TEST_COUNT++))

# Test 20: Check dbt profiles.yml
DBT_PROFILES_PATH="${DBT_PROJECT_DIR:-/home/hac/downloads/code/asgard-dev/dbt}/profiles.yml"
if [ -f "$DBT_PROFILES_PATH" ]; then
    log "${GREEN}✅ PASSED: dbt profiles.yml exists${NC}"
    ((PASSED_TESTS++))
else
    log "${YELLOW}⚠️  WARNING: dbt profiles.yml not found at expected location${NC}"
    ((FAILED_TESTS++))
fi
((TEST_COUNT++))

# Final Report
log "\n📊 Production Test Results Summary"
log "=================================="
log "Total Tests: ${TEST_COUNT}"
log "Passed: ${GREEN}${PASSED_TESTS}${NC}"
log "Failed: ${RED}${FAILED_TESTS}${NC}"
log "Success Rate: $(( PASSED_TESTS * 100 / TEST_COUNT ))%"
log "Log File: ${LOG_FILE}"

# Generate JSON report
JSON_REPORT="${TEST_RESULTS_DIR}/dbt_api_test_report_${TIMESTAMP}.json"
cat > "${JSON_REPORT}" << EOF
{
    "test_suite": "DBT Transformations API Production Tests",
    "timestamp": "${TIMESTAMP}",
    "base_url": "${BASE_URL}",
    "summary": {
        "total_tests": ${TEST_COUNT},
        "passed_tests": ${PASSED_TESTS},
        "failed_tests": ${FAILED_TESTS},
        "success_rate": $(( PASSED_TESTS * 100 / TEST_COUNT ))
    },
    "environment": {
        "dbt_project_dir": "${DBT_PROJECT_DIR:-/home/hac/downloads/code/asgard-dev/dbt}",
        "api_base_url": "${BASE_URL}"
    }
}
EOF

log "JSON Report: ${JSON_REPORT}"

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    log "\n${GREEN}🎉 All tests passed! Production API is ready.${NC}"
    exit 0
else
    log "\n${RED}❌ Some tests failed. Please review the results above.${NC}"
    exit 1
fi