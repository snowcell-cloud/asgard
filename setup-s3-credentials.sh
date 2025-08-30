#!/bin/bash

# Helper script to create S3 credentials secret
# Usage: ./setup-s3-credentials.sh <access-key> <secret-key> <region>

if [ $# -ne 3 ]; then
    echo "Usage: $0 <aws-access-key-id> <aws-secret-access-key> <aws-region>"
    echo "Example: $0 AKIAIOSFODNN7EXAMPLE wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY us-east-1"
    exit 1
fi

AWS_ACCESS_KEY_ID="$1"
AWS_SECRET_ACCESS_KEY="$2"
AWS_REGION="$3"

# Encode credentials
ACCESS_KEY_B64=$(echo -n "$AWS_ACCESS_KEY_ID" | base64 -w 0)
SECRET_KEY_B64=$(echo -n "$AWS_SECRET_ACCESS_KEY" | base64 -w 0)
REGION_B64=$(echo -n "$AWS_REGION" | base64 -w 0)

echo "Creating S3 credentials secret..."

# Create the secret for data-platform namespace
kubectl create secret generic s3-credentials \
  --namespace data-platform \
  --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  --from-literal=AWS_REGION="$AWS_REGION" \
  --dry-run=client -o yaml | kubectl apply -f -

# Create the secret for asgard namespace
kubectl create secret generic s3-credentials \
  --namespace asgard \
  --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  --from-literal=AWS_REGION="$AWS_REGION" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ S3 credentials created successfully!"
echo "Encoded values (for reference):"
echo "AWS_ACCESS_KEY_ID: $ACCESS_KEY_B64"
echo "AWS_SECRET_ACCESS_KEY: $SECRET_KEY_B64"
echo "AWS_REGION: $REGION_B64"
