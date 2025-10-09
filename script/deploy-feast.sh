#!/bin/bash
set -e

echo "🚀 Deploying Asgard Data Platform with Feast Feature Store"
echo "=========================================================="
echo ""

# Configuration
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG="feast-${TIMESTAMP}"
ECR_REGISTRY="637423187518.dkr.ecr.eu-north-1.amazonaws.com"
IMAGE_NAME="asgard"
NAMESPACE="asgard"

echo "📦 Build Configuration:"
echo "   Tag: ${TAG}"
echo "   Registry: ${ECR_REGISTRY}"
echo "   Image: ${IMAGE_NAME}"
echo ""

# Step 1: Build Docker image
echo "🔨 Step 1/5: Building Docker image..."
docker build -t ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG} .

echo ""
echo "✅ Docker image built successfully"
echo ""

# Step 2: Login to ECR
echo "🔐 Step 2/5: Logging into AWS ECR..."
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

echo ""
echo "✅ ECR login successful"
echo ""

# Step 3: Push image
echo "📤 Step 3/5: Pushing image to ECR..."
docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${TAG}

echo ""
echo "✅ Image pushed successfully"
echo ""

# Step 4: Deploy with Helm
echo "🚀 Step 4/5: Deploying to Kubernetes with Helm..."
helm upgrade --install asgard ./helmchart \
  --namespace ${NAMESPACE} \
  --create-namespace \
  --set image.tag=${TAG} \
  --wait \
  --timeout 10m

echo ""
echo "✅ Helm deployment successful"
echo ""

# Step 5: Verify deployment
echo "🔍 Step 5/5: Verifying deployment..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=asgard \
  -n ${NAMESPACE} \
  --timeout=300s

echo ""
echo "✅ All pods are ready"
echo ""

# Get service info
SERVICE_IP=$(kubectl get svc -n ${NAMESPACE} asgard-app -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "=========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================================="
echo ""
echo "📊 Deployment Information:"
echo "   Namespace: ${NAMESPACE}"
echo "   Image Tag: ${TAG}"
echo "   Service IP: ${SERVICE_IP:-Pending...}"
echo ""
echo "📡 API Endpoints:"
echo "   Health: http://${SERVICE_IP}/health"
echo "   API Docs: http://${SERVICE_IP}/docs"
echo "   DBT: http://${SERVICE_IP}/dbt"
echo "   Feast: http://${SERVICE_IP}/feast"
echo ""
echo "🧪 Quick Tests:"
echo ""
echo "# 1. Health Check"
echo "curl http://${SERVICE_IP}/health"
echo ""
echo "# 2. Feast Status"
echo "curl http://${SERVICE_IP}/feast/status"
echo ""
echo "# 3. Register Feature View"
echo "curl -X POST http://${SERVICE_IP}/feast/features \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"name\": \"test_features\", ...}'"
echo ""
echo "# 4. Train Model"
echo "curl -X POST http://${SERVICE_IP}/feast/models \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"name\": \"test_model\", ...}'"
echo ""
echo "📚 Documentation:"
echo "   - Quick Start: docs/FEAST_QUICK_START.md"
echo "   - Full Docs: docs/FEAST_FEATURE_STORE.md"
echo "   - Postman: docs/postman/feast_api_collection.json"
echo ""
echo "🔗 Useful Commands:"
echo "   View logs: kubectl logs -n ${NAMESPACE} -l app.kubernetes.io/name=asgard --tail=100 -f"
echo "   Get pods: kubectl get pods -n ${NAMESPACE}"
echo "   Describe: kubectl describe pod -n ${NAMESPACE} <pod-name>"
echo ""
echo "=========================================================="
