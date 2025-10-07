#!/bin/bash
set -e

echo "🔧 Fixed: transformation_id field name in service.py"
echo "   Changed 'id' to 'transformation_id' to match DBTTransformationResponse schema"
echo ""
echo "📦 Building Docker image..."
docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:schema-fix .

echo ""
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 637423187518.dkr.ecr.eu-north-1.amazonaws.com

echo ""
echo "📤 Pushing image to ECR..."
docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:schema-fix

echo ""
echo "🚀 Deploying to Kubernetes..."
helm upgrade --install asgard ./helmchart \
  --namespace asgard \
  --set image.tag=schema-fix \
  --wait

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🧪 Test with:"
echo "curl -X 'POST' 'http://51.89.225.64/dbt/transform' \\"
echo "  -H 'accept: application/json' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{...}'"
