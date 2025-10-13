#!/bin/bash
# Fix Feast S3 Region Configuration and Re-run Tests

set -e

echo "🔧 Fixing Feast S3 Region Configuration..."
echo ""

# Get the pod name
POD_NAME=$(kubectl get pods -n asgard -l app=asgard-app -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "❌ No asgard-app pod found"
    exit 1
fi

echo "📦 Found pod: $POD_NAME"
echo ""

# Create updated feature_store.yaml with S3 region
echo "📝 Creating updated feature_store.yaml..."

cat > /tmp/feature_store_updated.yaml <<'EOF'
project: asgard_features
registry: /tmp/feast_repo/registry.db
provider: local
offline_store:
    type: file
    # S3 configuration for Iceberg/Parquet files
    # Reads directly from: s3://airbytedestination1/iceberg/gold/{table}/data/*.parquet
    region: eu-north-1
entity_key_serialization_version: 2
EOF

echo "✅ Created updated configuration"
cat /tmp/feature_store_updated.yaml
echo ""

# Copy the file to the pod
echo "📤 Uploading to pod..."
kubectl cp /tmp/feature_store_updated.yaml asgard/$POD_NAME:/tmp/feast_repo/feature_store.yaml

echo "✅ Configuration updated in pod"
echo ""

# Verify the update
echo "🔍 Verifying configuration..."
kubectl exec -n asgard $POD_NAME -- cat /tmp/feast_repo/feature_store.yaml

echo ""
echo "✅ Feast configuration fixed!"
echo ""
echo "🧪 Now running tests..."
echo ""

# Run the tests
python3 test_feast_api_real_table.py
