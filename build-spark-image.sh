#!/bin/bash
# Script to build and push custom Spark image with S3A support

set -e

ECR_REGISTRY="637423187518.dkr.ecr.eu-north-1.amazonaws.com"
ECR_REPOSITORY="spark-custom"
IMAGE_TAG="${1:-latest}"
REGION="eu-north-1"

FULL_IMAGE="$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"

echo "🏗️ Building custom Spark image with S3A support..."
echo "Image: $FULL_IMAGE"
echo "Region: $REGION"
echo ""

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build the image
echo "🔨 Building Docker image..."
docker build -f spark.Dockerfile -t $FULL_IMAGE .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Push the image
    echo "📤 Pushing image to ECR..."
    docker push $FULL_IMAGE
    
    if [ $? -eq 0 ]; then
        echo "✅ Image pushed successfully!"
        echo ""
        echo "🎉 Custom Spark image is ready:"
        echo "   $FULL_IMAGE"
        echo ""
        echo "📝 To use this image, update your environment variable:"
        echo "   export SPARK_IMAGE=\"$FULL_IMAGE\""
        echo ""
        echo "🚀 Or update the API client default image."
    else
        echo "❌ Failed to push image"
        exit 1
    fi
else
    echo "❌ Build failed"
    exit 1
fi
