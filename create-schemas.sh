#!/bin/bash

# Create Required Schemas in Trino/Iceberg

set -e

echo "🔧 Creating Required Schemas in Iceberg Catalog"
echo "==============================================="
echo ""

TRINO_HOST="trino.data-platform.svc.cluster.local"
TRINO_PORT="8080"

# Function to create schema via Trino REST API
create_schema() {
    local schema_name=$1
    echo "Creating schema: iceberg.$schema_name"
    
    kubectl run -n asgard create-schema-$schema_name --image=curlimages/curl --rm -i --restart=Never -- sh -c "
    curl -s -X POST 'http://$TRINO_HOST:$TRINO_PORT/v1/statement' \
      -H 'X-Trino-User: dbt' \
      -H 'X-Trino-Catalog: iceberg' \
      -H 'X-Trino-Schema: default' \
      -d 'CREATE SCHEMA IF NOT EXISTS iceberg.$schema_name'
    " 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Schema created: iceberg.$schema_name"
    else
        echo "❌ Failed to create schema: iceberg.$schema_name"
        return 1
    fi
}

# Create silver schema
echo "Step 1: Creating silver schema..."
create_schema "silver"
echo ""

# Create gold schema
echo "Step 2: Creating gold schema..."
create_schema "gold"
echo ""

# Verify schemas exist
echo "Step 3: Verifying schemas..."
echo "Listing all schemas in iceberg catalog:"

kubectl run -n asgard list-schemas --image=curlimages/curl --rm -i --restart=Never -- sh -c "
curl -s -X POST 'http://$TRINO_HOST:$TRINO_PORT/v1/statement' \
  -H 'X-Trino-User: dbt' \
  -H 'X-Trino-Catalog: iceberg' \
  -H 'X-Trino-Schema: default' \
  -d 'SHOW SCHEMAS'
" 2>/dev/null | grep -o '"data":\[\[.*\]\]' || echo "Could not fetch schemas"

echo ""
echo "✅ Schema creation complete!"
echo ""
echo "Next steps:"
echo "1. Deploy the updated application:"
echo "   docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest ."
echo "   docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest"
echo "   helm upgrade --install asgard ./helmchart -n asgard"
echo ""
echo "2. Test the transformation API:"
echo "   curl -X POST http://51.89.225.64/dbt/transform \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"name\":\"test\",\"sql_query\":\"SELECT 1 as col\",\"description\":\"test\",\"materialization\":\"table\",\"owner\":\"admin\"}'"