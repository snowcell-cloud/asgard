#!/bin/bash

# MLflow Deployment Script for Kubernetes
# This script deploys MLflow and its dependencies to the asgard namespace

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}MLflow Kubernetes Deployment${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if s3-credentials secret exists
if ! kubectl get secret s3-credentials -n asgard &> /dev/null; then
    echo -e "${RED}Error: s3-credentials secret does not exist${NC}"
    echo -e "${YELLOW}Please create the secret first:${NC}"
    echo ""
    echo "  kubectl create secret generic s3-credentials \\"
    echo "    --from-literal=AWS_ACCESS_KEY_ID=your-access-key \\"
    echo "    --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key \\"
    echo "    --from-literal=AWS_REGION=us-east-1 \\"
    echo "    --from-literal=AWS_S3_BUCKET=your-mlflow-bucket \\"
    echo "    -n asgard"
    echo ""
    echo "Or see s3-credentials-template.yaml for reference"
    exit 1
fi

# Check if asgard namespace exists
if ! kubectl get namespace asgard &> /dev/null; then
    echo -e "${YELLOW}Warning: asgard namespace does not exist${NC}"
    echo -e "${YELLOW}Creating asgard namespace...${NC}"
    kubectl create namespace asgard
    kubectl label namespace asgard name=asgard app=asgard-data-platform
fi

echo -e "${GREEN}[1/6] Deploying Storage (PVCs)...${NC}"
kubectl apply -f storage.yaml
sleep 2

echo -e "${GREEN}[2/4] Deploying PostgreSQL...${NC}"
kubectl apply -f postgres.yaml
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l component=postgres -n asgard --timeout=300s

echo -e "${GREEN}[3/4] Deploying MLflow Tracking Server...${NC}"
kubectl apply -f mlflow-deployment.yaml
kubectl apply -f mlflow-service.yaml
echo -e "${YELLOW}Waiting for MLflow to be ready...${NC}"
kubectl wait --for=condition=ready pod -l component=tracking-server -n asgard --timeout=300s

echo -e "${GREEN}[4/4] Deploying MLflow Ingress...${NC}"
kubectl apply -f mlflow-ingress.yaml

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Display deployment status
echo -e "${GREEN}Deployment Status:${NC}"
kubectl get pods -n asgard -l app=mlflow
echo ""

echo -e "${GREEN}Services:${NC}"
kubectl get svc -n asgard -l app=mlflow
echo ""

echo -e "${GREEN}Ingress:${NC}"
kubectl get ingress -n asgard mlflow-ingress
echo ""

# Display access information
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Access Information${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Option 1: Port Forward (Development)${NC}"
echo "  kubectl port-forward -n asgard svc/mlflow-service 5000:5000"
echo "  Access MLflow at: http://localhost:5000"
echo ""
echo -e "${YELLOW}Option 2: Ingress (Production)${NC}"
echo "  Update the host in mlflow-ingress.yaml to your domain"
echo "  Access MLflow at: http://mlflow.asgard.local (or your configured domain)"
echo ""
echo -e "${YELLOW}S3 Bucket:${NC}"
S3_BUCKET=$(kubectl get secret s3-credentials -n asgard -o jsonpath='{.data.AWS_S3_BUCKET}' | base64 -d)
AWS_REGION=$(kubectl get secret s3-credentials -n asgard -o jsonpath='{.data.AWS_REGION}' | base64 -d)
echo "  Bucket: $S3_BUCKET"
echo "  Region: $AWS_REGION"
echo "  Access via AWS Console or CLI"
echo ""

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Next Steps${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "1. Update default passwords in production"
echo "2. Configure TLS/SSL for secure access"
echo "3. Set up proper ingress with your domain"
echo "4. Configure backup strategies"
echo "5. Review and apply network policies"
echo ""
echo -e "${GREEN}For more information, see README.md${NC}"
