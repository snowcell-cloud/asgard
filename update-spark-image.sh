#!/bin/bash

# Script to update Spark image in Helm values
# Usage: ./update-spark-image.sh [IMAGE_TAG]

ECR_REGISTRY="637423187518.dkr.ecr.eu-north-1.amazonaws.com"
ECR_REPOSITORY="spark-custom"
IMAGE_TAG="${1:-latest}"

FULL_IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

echo "🔄 Updating Spark image to: $FULL_IMAGE"

# Update Helm values
if [ -f "helmchart/values.yaml" ]; then
    # Use sed to update the SPARK_IMAGE environment variable
    sed -i "s|SPARK_IMAGE: \".*\"|SPARK_IMAGE: \"$FULL_IMAGE\"|g" helmchart/values.yaml
    echo "✅ Updated helmchart/values.yaml"
    
    # Show the change
    echo "📋 Current SPARK_IMAGE setting:"
    grep "SPARK_IMAGE:" helmchart/values.yaml
else
    echo "❌ helmchart/values.yaml not found"
    exit 1
fi

echo ""
echo "🚀 To apply the change, run:"
echo "helm upgrade asgard ./helmchart --namespace asgard"
