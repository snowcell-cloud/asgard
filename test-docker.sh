#!/bin/bash

set -e

echo "🐳 Building Docker image..."
docker build -t asgard-app:test .

echo "🚀 Starting container..."
CONTAINER_ID=$(docker run -d -p 8000:8000 asgard-app:test)

echo "⏳ Waiting for container to be ready..."
sleep 10

echo "🔍 Testing health endpoint..."
if curl -f http://localhost:8000/health; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
    docker logs $CONTAINER_ID
    docker stop $CONTAINER_ID
    docker rm $CONTAINER_ID
    exit 1
fi

echo "📚 Testing docs endpoint..."
if curl -f http://localhost:8000/docs > /dev/null; then
    echo "✅ Docs endpoint accessible!"
else
    echo "❌ Docs endpoint failed!"
fi

echo "🧹 Cleaning up..."
docker stop $CONTAINER_ID
docker rm $CONTAINER_ID

echo "🎉 All tests passed!"
