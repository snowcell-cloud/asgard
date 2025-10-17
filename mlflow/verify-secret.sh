#!/bin/bash

# S3 Credentials Verification Script
# This script verifies that the s3-credentials secret is properly configured

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}S3 Credentials Verification${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

NAMESPACE="asgard"
SECRET_NAME="s3-credentials"

# Check if secret exists
echo -e "${YELLOW}[1/5] Checking if secret exists...${NC}"
if kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} &> /dev/null; then
    echo -e "${GREEN}✓ Secret '${SECRET_NAME}' exists in namespace '${NAMESPACE}'${NC}"
else
    echo -e "${RED}✗ Secret '${SECRET_NAME}' not found in namespace '${NAMESPACE}'${NC}"
    echo ""
    echo "Create the secret with:"
    echo "  kubectl create secret generic s3-credentials \\"
    echo "    --from-literal=AWS_ACCESS_KEY_ID=your-access-key \\"
    echo "    --from-literal=AWS_SECRET_ACCESS_KEY=your-secret-key \\"
    echo "    --from-literal=AWS_REGION=us-east-1 \\"
    echo "    --from-literal=AWS_S3_BUCKET=your-mlflow-bucket \\"
    echo "    -n asgard"
    exit 1
fi

echo ""

# Check required fields
REQUIRED_FIELDS=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "AWS_REGION" "AWS_S3_BUCKET")

echo -e "${YELLOW}[2/5] Checking required fields...${NC}"
MISSING_FIELDS=()

for field in "${REQUIRED_FIELDS[@]}"; do
    if kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath="{.data.${field}}" &> /dev/null; then
        VALUE=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath="{.data.${field}}" | base64 -d)
        if [ -n "$VALUE" ]; then
            echo -e "${GREEN}✓ ${field}: ${VALUE:0:10}...${NC}"
        else
            echo -e "${RED}✗ ${field}: (empty)${NC}"
            MISSING_FIELDS+=("${field}")
        fi
    else
        echo -e "${RED}✗ ${field}: (missing)${NC}"
        MISSING_FIELDS+=("${field}")
    fi
done

if [ ${#MISSING_FIELDS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Error: Missing or empty fields: ${MISSING_FIELDS[*]}${NC}"
    exit 1
fi

echo ""

# Decode and show values
echo -e "${YELLOW}[3/5] Secret values:${NC}"
AWS_ACCESS_KEY_ID=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_REGION=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_REGION}' | base64 -d)
AWS_S3_BUCKET=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_S3_BUCKET}' | base64 -d)

echo "  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}...${AWS_ACCESS_KEY_ID: -4}"
echo "  AWS_REGION: ${AWS_REGION}"
echo "  AWS_S3_BUCKET: ${AWS_S3_BUCKET}"
echo "  AWS_SECRET_ACCESS_KEY: ********** (hidden)"

echo ""

# Test AWS credentials (optional, requires aws cli)
if command -v aws &> /dev/null; then
    echo -e "${YELLOW}[4/5] Testing AWS credentials...${NC}"
    
    export AWS_ACCESS_KEY_ID=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
    export AWS_SECRET_ACCESS_KEY=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
    export AWS_DEFAULT_REGION=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_REGION}' | base64 -d)
    
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}✓ AWS credentials are valid${NC}"
        aws sts get-caller-identity
    else
        echo -e "${RED}✗ AWS credentials are invalid or expired${NC}"
    fi
    
    echo ""
    
    echo -e "${YELLOW}[5/5] Testing S3 bucket access...${NC}"
    S3_BUCKET=$(kubectl get secret ${SECRET_NAME} -n ${NAMESPACE} -o jsonpath='{.data.AWS_S3_BUCKET}' | base64 -d)
    
    if aws s3 ls s3://${S3_BUCKET} &> /dev/null; then
        echo -e "${GREEN}✓ S3 bucket '${S3_BUCKET}' is accessible${NC}"
    else
        echo -e "${RED}✗ Cannot access S3 bucket '${S3_BUCKET}'${NC}"
        echo "  Make sure the bucket exists and credentials have proper permissions"
    fi
else
    echo -e "${YELLOW}[4/5] Skipping AWS credentials test (aws cli not installed)${NC}"
    echo -e "${YELLOW}[5/5] Skipping S3 bucket test (aws cli not installed)${NC}"
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Verification Summary${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${GREEN}✓ Secret structure is correct${NC}"
echo -e "${GREEN}✓ All required fields are present${NC}"
echo ""
echo "Next steps:"
echo "  1. Deploy MLflow: cd mlflow && ./deploy.sh"
echo "  2. Test connection: python test-connection.py"
echo ""
