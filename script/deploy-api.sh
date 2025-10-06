#!/bin/bash

# Script to deploy the Data Products API to Kubernetes

echo "🚀 Deploying Asgard Data Products API to Kubernetes..."

# Create ConfigMap with application code
echo "📦 Creating ConfigMap with application code..."
kubectl create configmap asgard-app-code \
  --from-file=app/ \
  --from-file=dbt/ \
  --from-file=requirements.txt \
  --from-file=pyproject.toml \
  --dry-run=client -o yaml | kubectl apply -f - -n asgard

# Deploy the API
echo "🚢 Deploying API to Kubernetes..."
kubectl apply -f k8s/data-products-api.yaml

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/asgard-data-products-api -n asgard

# Show status
echo "📊 Deployment Status:"
kubectl get pods -l app=asgard-data-products-api -n asgard
kubectl get svc asgard-data-products-api -n asgard

echo "✅ API deployed successfully!"
echo "🌐 Access the API at: kubectl port-forward -n asgard svc/asgard-data-products-api 8000:8000"