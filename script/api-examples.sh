#!/bin/bash

# API Testing Documentation and Examples
# This script provides comprehensive examples of all API endpoints

echo "📚 DATA PRODUCTS API - COMPREHENSIVE TESTING GUIDE"
echo "=================================================="
echo ""

API_BASE="http://localhost:8000"

echo "🔧 API Base URL: $API_BASE"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_section() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '%.0s-' {1..${#1}})"
}

print_endpoint() {
    echo -e "${GREEN}$1${NC}"
}

print_example() {
    echo -e "${YELLOW}$1${NC}"
}

echo "🏥 1. HEALTH CHECK"
print_section "Health Check Endpoint"
print_endpoint "GET /health"
echo "Description: Check if the API is running and healthy"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/health\""
echo ""
print_example "Expected Response:"
echo '{"status": "healthy", "timestamp": "2024-01-20T10:00:00Z"}'
echo ""
echo ""

echo "📋 2. DATA PRODUCTS MANAGEMENT"
print_section "List All Data Products"
print_endpoint "GET /api/v1/data-products/"
echo "Description: Retrieve all data products with optional filtering"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/data-products/\""
echo ""
print_example "With filters:"
echo "curl -X GET \"$API_BASE/api/v1/data-products/?owner=team-analytics&data_product_type=CUSTOMER_360\""
echo ""
echo ""

print_section "Create Data Product"
print_endpoint "POST /api/v1/data-products/"
echo "Description: Create a new data product"
echo ""
print_example "Example - Customer 360:"
cat << 'EOF'
curl -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer 360 Analytics",
    "description": "Comprehensive customer view combining transactions, demographics, and behavior",
    "data_product_type": "CUSTOMER_360",
    "source_query": "SELECT c.customer_id, c.name, c.email, c.registration_date, SUM(o.amount) as total_spend, COUNT(o.order_id) as order_count FROM test_persistence.customers c LEFT JOIN test_persistence.orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.name, c.email, c.registration_date",
    "owner": "team-analytics",
    "consumers": ["team-marketing", "team-sales"],
    "update_frequency": "daily",
    "sla_hours": 24,
    "tags": ["customer", "analytics", "360-view"]
  }'
EOF
echo ""
echo ""

print_example "Example - Revenue Analysis:"
cat << 'EOF'
curl -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Revenue Analysis Dashboard",
    "description": "Monthly revenue breakdown by product category and region",
    "data_product_type": "REPORTING",
    "source_query": "SELECT DATE_TRUNC('\''month'\'', order_date) as month, product_category, region, SUM(amount) as revenue, COUNT(*) as transaction_count FROM test_persistence.sales_data WHERE order_date >= DATE_SUB(CURRENT_DATE, INTERVAL 12 MONTH) GROUP BY DATE_TRUNC('\''month'\'', order_date), product_category, region ORDER BY month DESC",
    "owner": "team-finance",
    "consumers": ["team-executives", "team-sales"],
    "update_frequency": "weekly",
    "sla_hours": 48,
    "tags": ["revenue", "reporting", "monthly"]
  }'
EOF
echo ""
echo ""

print_section "Get Data Product Details"
print_endpoint "GET /api/v1/data-products/{id}"
echo "Description: Retrieve detailed information about a specific data product"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef\""
echo ""
echo ""

print_section "Update Data Product"
print_endpoint "PUT /api/v1/data-products/{id}"
echo "Description: Update an existing data product (partial updates supported)"
echo ""
print_example "Example:"
cat << 'EOF'
curl -X PUT "$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description with enhanced analytics capabilities",
    "consumers": ["team-marketing", "team-sales", "team-product"],
    "update_frequency": "hourly",
    "tags": ["customer", "analytics", "360-view", "enhanced"]
  }'
EOF
echo ""
echo ""

print_section "Delete Data Product"
print_endpoint "DELETE /api/v1/data-products/{id}"
echo "Description: Delete a data product and its associated resources"
echo ""
print_example "Example:"
echo "curl -X DELETE \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef\""
echo ""
echo ""

echo "🔄 3. DATA PRODUCT OPERATIONS"
print_section "Run Data Product Transformation"
print_endpoint "POST /api/v1/data-products/{id}/run"
echo "Description: Execute the data transformation to create/update the gold layer table"
echo ""
print_example "Example:"
echo "curl -X POST \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef/run\""
echo ""
print_example "Expected Response:"
echo '{"status": "success", "message": "Data product transformation completed", "execution_time": "45.2s", "rows_processed": 150000}'
echo ""
echo ""

print_section "Get Data Product Statistics"
print_endpoint "GET /api/v1/data-products/{id}/stats"
echo "Description: Retrieve statistics about the data product's gold layer table"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef/stats\""
echo ""
print_example "Expected Response:"
echo '{"table_name": "iceberg.gold.customer_360_analytics_01234567", "row_count": 150000, "last_updated": "2024-01-20T10:30:00Z", "size_mb": 245.8, "status": "available"}'
echo ""
echo ""

print_section "Validate Data Product"
print_endpoint "POST /api/v1/data-products/{id}/validate"
echo "Description: Run validation checks on the data product's configuration and data quality"
echo ""
print_example "Example:"
echo "curl -X POST \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef/validate\""
echo ""
print_example "Expected Response:"
echo '{"validation_status": "passed", "checks_performed": ["schema_validation", "data_quality", "referential_integrity"], "issues": [], "score": 100}'
echo ""
echo ""

print_section "Preview Data Product"
print_endpoint "GET /api/v1/data-products/{id}/preview"
echo "Description: Get a sample of the data product's output (limited rows)"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/data-products/01234567-89ab-cdef-0123-456789abcdef/preview?limit=10\""
echo ""
echo ""

echo "📊 4. DATA CATALOG OPERATIONS"
print_section "List Data Sources"
print_endpoint "GET /api/v1/catalog/sources"
echo "Description: List available data sources from the catalog"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/catalog/sources\""
echo ""
echo ""

print_section "Get Table Schema"
print_endpoint "GET /api/v1/catalog/sources/{source}/tables/{table}/schema"
echo "Description: Get the schema information for a specific table"
echo ""
print_example "Example:"
echo "curl -X GET \"$API_BASE/api/v1/catalog/sources/test_persistence/tables/customers/schema\""
echo ""
echo ""

echo "🧪 5. COMPLETE WORKFLOW EXAMPLE"
print_section "End-to-End Data Product Creation and Execution"
echo "This example shows a complete workflow from creation to execution:"
echo ""

cat << 'EOF'
# Step 1: Create a data product
RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Segmentation Analysis",
    "description": "Customer segmentation based on purchase behavior and demographics",
    "data_product_type": "CUSTOMER_360",
    "source_query": "SELECT customer_id, CASE WHEN total_spend > 1000 THEN '\''high_value'\'' WHEN total_spend > 500 THEN '\''medium_value'\'' ELSE '\''low_value'\'' END as segment, total_spend, order_count FROM test_persistence.customer_summary",
    "owner": "team-marketing",
    "consumers": ["team-sales"],
    "update_frequency": "daily",
    "tags": ["segmentation", "marketing"]
  }')

# Step 2: Extract the data product ID
DATA_PRODUCT_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created data product: $DATA_PRODUCT_ID"

# Step 3: Run the transformation
curl -X POST "$API_BASE/api/v1/data-products/$DATA_PRODUCT_ID/run"

# Step 4: Check the results
curl -X GET "$API_BASE/api/v1/data-products/$DATA_PRODUCT_ID/stats"

# Step 5: Preview the data
curl -X GET "$API_BASE/api/v1/data-products/$DATA_PRODUCT_ID/preview?limit=5"

# Step 6: Validate the data product
curl -X POST "$API_BASE/api/v1/data-products/$DATA_PRODUCT_ID/validate"
EOF
echo ""
echo ""

echo "🔍 6. COMMON USE CASES"
print_section "Customer Analytics"
cat << 'EOF'
# Customer lifetime value calculation
curl -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Lifetime Value",
    "data_product_type": "CUSTOMER_360",
    "source_query": "SELECT customer_id, AVG(order_value) * COUNT(*) * 12 as estimated_clv, first_purchase_date, last_purchase_date FROM test_persistence.customer_orders GROUP BY customer_id, first_purchase_date, last_purchase_date",
    "owner": "team-analytics"
  }'
EOF
echo ""

print_section "Sales Reporting"
cat << 'EOF'
# Daily sales summary
curl -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Sales Summary",
    "data_product_type": "REPORTING", 
    "source_query": "SELECT DATE(order_date) as sales_date, COUNT(*) as total_orders, SUM(amount) as total_revenue, AVG(amount) as avg_order_value FROM test_persistence.orders WHERE order_date >= CURRENT_DATE - INTERVAL 30 DAY GROUP BY DATE(order_date) ORDER BY sales_date DESC",
    "owner": "team-sales"
  }'
EOF
echo ""

print_section "Product Performance"
cat << 'EOF'
# Product performance metrics
curl -X POST "$API_BASE/api/v1/data-products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Performance Metrics",
    "data_product_type": "PRODUCT_ANALYTICS",
    "source_query": "SELECT product_id, product_name, SUM(quantity_sold) as total_sold, SUM(revenue) as total_revenue, AVG(customer_rating) as avg_rating FROM test_persistence.product_sales GROUP BY product_id, product_name ORDER BY total_revenue DESC",
    "owner": "team-product"
  }'
EOF
echo ""
echo ""

echo "🚨 7. ERROR HANDLING"
print_section "Common Error Responses"
echo "400 Bad Request - Invalid input data"
echo "404 Not Found - Data product or resource not found"
echo "500 Internal Server Error - Server-side processing error"
echo ""
print_example "Example error response:"
echo '{"error": "validation_failed", "message": "Invalid source_query: syntax error", "details": ["Line 1: Unexpected token SELECT"]}'
echo ""
echo ""

echo "🔧 8. TESTING UTILITIES"
print_section "Quick Health Check"
echo "curl -f $API_BASE/health || echo 'API is not responding'"
echo ""

print_section "List All Data Products"
echo "curl -s $API_BASE/api/v1/data-products/ | python3 -m json.tool"
echo ""

print_section "Clean Up Test Data Products"
cat << 'EOF'
# Get all data products with 'test' in the name and delete them
curl -s "$API_BASE/api/v1/data-products/" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
for dp in data:
    if 'test' in dp['name'].lower():
        print(f'Deleting test data product: {dp[\"id\"]} - {dp[\"name\"]}')
        # Uncomment the next line to actually delete
        # os.system(f'curl -X DELETE \"$API_BASE/api/v1/data-products/{dp[\"id\"]}\"')
"
EOF
echo ""
echo ""

echo "✅ READY TO TEST!"
echo "=================="
echo "1. Ensure the API is running: ./deploy-production.sh status"
echo "2. Set up port-forwarding: kubectl port-forward -n asgard svc/asgard-data-products-api 8000:8000"
echo "3. Run health check: curl $API_BASE/health"
echo "4. Start testing with the examples above!"
echo ""
echo "For automated testing, use: ./test-production.sh"