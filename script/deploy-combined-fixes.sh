#!/bin/bash
set -e

echo "🔧 FIXES APPLIED:"
echo "   1. Removed +schema: gold from dbt_project.yml (prevents gold_gold duplication)"
echo "   2. Removed schema from model config (lets profiles.yml handle it)"
echo "   3. Fixed transformation_id field name mismatch"
echo ""

# Get current timestamp for tag
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG="fix-combined-${TIMESTAMP}"

echo "📦 Building Docker image with tag: ${TAG}"
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TAG} .

echo ""
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com

echo ""
echo "📤 Pushing image to ECR..."
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:${TAG}

echo ""
echo "🚀 Deploying to Kubernetes..."
helm upgrade --install asgard ./helmchart \
  --namespace asgard \
  --set image.tag=${TAG} \
  --wait \
  --timeout 5m

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "🔍 Verify deployment:"
echo "kubectl get pods -n asgard"
echo "kubectl logs -n asgard -l app.kubernetes.io/name=asgard --tail=50"
echo ""
echo "🧪 Test transformation:"
echo "curl -X 'POST' 'http://51.89.225.64/dbt/transform' \\"
echo "  -H 'accept: application/json' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '  "name": "test_correct_schema",'
echo '  "sql_query": "SELECT order_id, product_id, produced_units FROM iceberg.silver.t2c60d13e WHERE produced_units > 0 LIMIT 10",'
echo '  "description": "Testing gold schema fix",'
echo '  "materialization": "table",'
echo '  "owner": "dbt"'
echo "}'"
echo ""
echo "✅ Expected: Table created in iceberg.gold.test_correct_schema"
echo "❌ Should NOT create: iceberg.gold_gold.test_correct_schema"
