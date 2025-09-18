#!/bin/bash
# Script to create ECR ImagePullSecret for Spark jobs

set -e

echo "🔐 Setting up ECR authentication for Spark jobs..."

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Check if we have AWS credentials
if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
    echo "❌ AWS credentials not set. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    exit 1
fi

# ECR repository details
ECR_REGISTRY="637423187518.dkr.ecr.eu-north-1.amazonaws.com"
ECR_REGION="eu-north-1"

echo "📡 Getting ECR login token..."

# Get ECR login token
TOKEN=$(aws ecr get-login-password --region $ECR_REGION)

if [[ -z "$TOKEN" ]]; then
    echo "❌ Failed to get ECR login token"
    exit 1
fi

echo "✅ ECR token obtained"

# Create ImagePullSecret
echo "🔧 Creating ImagePullSecret..."
kubectl create secret docker-registry ecr-secret \
    --docker-server=$ECR_REGISTRY \
    --docker-username=AWS \
    --docker-password=$TOKEN \
    --namespace=asgard \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ ECR ImagePullSecret created successfully"

# Update the service account to use the ImagePullSecret
echo "🔧 Updating service account..."
kubectl patch serviceaccount spark-sa -n asgard -p '{"imagePullSecrets": [{"name": "ecr-secret"}]}'

echo "✅ Service account updated with ECR secret"

echo "🎉 ECR authentication setup complete!"
echo ""
echo "Your Spark jobs can now pull images from:"
echo "  $ECR_REGISTRY/spark-custom:latest"
