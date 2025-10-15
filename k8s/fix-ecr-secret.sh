#!/bin/bash

# Fix ECR secret name mismatch issue
# This script will:
# 1. Delete the old incorrectly named secret
# 2. Create the correctly named secret
# 3. Reapply the updated CronJob

set -e

ECR_REGISTRY="637423187518.dkr.ecr.eu-north-1.amazonaws.com"
AWS_REGION="eu-north-1"
NAMESPACE="asgard"

echo "🔧 Fixing ECR secret name mismatch..."

# Check if namespace exists
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
    echo "❌ Namespace '${NAMESPACE}' does not exist. Creating it..."
    kubectl create namespace ${NAMESPACE}
fi

# Delete old incorrectly named secret if it exists
echo "🗑️  Deleting old secret 'ecr-credentials' if it exists..."
kubectl delete secret ecr-credentials -n ${NAMESPACE} --ignore-not-found=true

# Get ECR login password
echo "🔐 Getting ECR login credentials..."
ECR_PASSWORD=$(aws ecr get-login-password --region ${AWS_REGION})

# Create docker config JSON
DOCKER_CONFIG_JSON=$(cat <<EOF
{
  "auths": {
    "${ECR_REGISTRY}": {
      "username": "AWS",
      "password": "${ECR_PASSWORD}"
    }
  }
}
EOF
)

# Delete and recreate the correctly named secret
echo "🔑 Creating new secret 'ecr-secret'..."
kubectl delete secret ecr-secret -n ${NAMESPACE} --ignore-not-found=true
kubectl create secret docker-registry ecr-secret \
  --docker-server=${ECR_REGISTRY} \
  --docker-username=AWS \
  --docker-password="${ECR_PASSWORD}" \
  -n ${NAMESPACE}

# Verify secret was created
echo "✅ Verifying secret creation..."
kubectl get secret ecr-secret -n ${NAMESPACE}

# Reapply the updated CronJob configuration
echo "🔄 Reapplying ECR credentials CronJob with corrected secret name..."
kubectl apply -f k8s/ecr-credentials.yaml

# Restart the deployment to pick up the new secret
echo "♻️  Restarting asgard deployment..."
kubectl rollout restart deployment -n ${NAMESPACE} -l app=asgard-app 2>/dev/null || \
kubectl rollout restart deployment asgard-app -n ${NAMESPACE} 2>/dev/null || \
echo "⚠️  Could not auto-restart deployment. Please restart manually."

echo ""
echo "✅ ECR secret fix complete!"
echo ""
echo "Next steps:"
echo "1. Check the deployment status: kubectl get pods -n ${NAMESPACE}"
echo "2. If pods are still in ImagePullBackOff, delete them to force recreation:"
echo "   kubectl delete pods -n ${NAMESPACE} -l app=asgard-app"
echo "3. Monitor the CronJob: kubectl get cronjob ecr-secret-refresh -n ${NAMESPACE}"
echo "4. To manually trigger the CronJob, run:"
echo "   kubectl create job --from=cronjob/ecr-secret-refresh ecr-secret-refresh-manual -n ${NAMESPACE}"
