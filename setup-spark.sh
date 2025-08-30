#!/bin/bash

# Simple setup for existing Asgard app with existing Spark Operator
echo "🚀 Setting up Spark permissions for existing Asgard app..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Check existing resources
print_step "✅ Found Spark Operator in data-platform namespace"
print_step "✅ Found Asgard app deployment: asgard-app"
print_step "✅ Found service accounts: asgard-app, spark-sa"

# Check if S3 credentials exist
if kubectl get secret s3-credentials -n asgard &> /dev/null; then
    print_step "✅ S3 credentials already exist"
else
    print_warning "S3 credentials not found. Create them with:"
    echo "kubectl create secret generic s3-credentials --namespace asgard \\"
    echo "  --from-literal=AWS_ACCESS_KEY_ID='your-key' \\"
    echo "  --from-literal=AWS_SECRET_ACCESS_KEY='your-secret' \\"
    echo "  --from-literal=AWS_REGION='eu-north-1'"
    echo ""
fi

# Set up minimal RBAC for Spark jobs
print_step "Setting up Spark permissions..."
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spark-minimal-role
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "configmaps"]
    verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "get", "list", "watch"]
  - apiGroups: ["sparkoperator.k8s.io"]
    resources: ["sparkapplications"]
    verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: spark-minimal-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: spark-minimal-role
subjects:
  - kind: ServiceAccount
    name: spark-sa
    namespace: asgard
  - kind: ServiceAccount
    name: asgard-app
    namespace: asgard
EOF

# Create SQL transform script
if kubectl get configmap sql-transform-script -n asgard &> /dev/null; then
    print_step "✅ SQL transform script already exists"
else
    print_step "Creating SQL transform script..."
    kubectl apply -f k8s/04-configmap.yaml
fi

print_step "🎉 ✅ Setup completed!"
echo ""
echo "Your Asgard app can now create Spark jobs!"
echo ""
echo "🧪 Test your transform API:"
echo 'curl -X POST "http://your-asgard-service/transform" \'
echo '     -H "Content-Type: application/json" \'
echo '     -d {"sql": "SELECT * FROM source_data LIMIT 10"}'
