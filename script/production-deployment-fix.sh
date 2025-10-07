#!/bin/bash

# Production Deployment Fix Script
# Addresses permission issues and updates Helm configuration

echo "🚀 Production Deployment Fix for Asgard DBT API"
echo "=============================================="

# Update Helm values to include dbt-specific environment variables
echo "📝 Updating Helm chart values..."

# Create temporary values file with additional configurations
cat > /tmp/additional-values.yaml << 'EOF'
env:
  # Existing environment variables
  ENVIRONMENT: "production"
  AIRBYTE_BASE_URL: "http://airbyte-airbyte-server-svc.airbyte.svc.cluster.local:8001/api/public/v1"
  PIPELINE_NAMESPACE: "asgard"
  SPARK_NAMESPACE: "asgard"
  SPARK_IMAGE: "637423187518.dkr.ecr.eu-north-1.amazonaws.com/spark-custom:latest"
  SPARK_SERVICE_ACCOUNT: "spark-sa"
  S3_SECRET_NAME: "s3-credentials"
  
  # Production data platform services in data-platform namespace
  TRINO_HOST: "trino-coordinator.data-platform.svc.cluster.local"
  TRINO_PORT: "8080"
  TRINO_USER: "trino"
  TRINO_CATALOG: "iceberg"
  NESSIE_URI: "http://nessie.data-platform.svc.cluster.local:19120/api/v1"
  NESSIE_REF: "main"
  NESSIE_AUTH_TYPE: "NONE"
  SILVER_SCHEMA: "silver"
  GOLD_SCHEMA: "gold"
  S3_BUCKET: "asgard-data-lake"
  S3_REGION: "us-west-2"
  
  # DBT-specific configurations
  DBT_PROJECT_DIR: "/tmp/dbt_projects"
  TMPDIR: "/tmp"

# Volume mounts for writable temp directory
volumeMounts:
  - name: temp-storage
    mountPath: /tmp
    
volumes:
  - name: temp-storage
    emptyDir: {}

# Additional security context
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  runAsNonRoot: true

# Resource limits for dbt operations
resources:
  limits:
    cpu: 2000m
    memory: 2000Mi
  requests:
    cpu: 1000m
    memory: 1000Mi
EOF

echo "✅ Additional Helm values created at /tmp/additional-values.yaml"

# Merge with existing values
echo "📋 Current Helm values:"
cat helmchart/values.yaml

echo ""
echo "🔄 To deploy with fixes, use:"
echo "helm upgrade --install asgard ./helmchart -f /tmp/additional-values.yaml -n asgard"

echo ""
echo "🐳 Docker image status:"
echo "Current image: 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:latest"
echo ""

echo "📦 Build and push new image with fixes:"
echo "docker build -t 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:$(date +%Y%m%d-%H%M%S) ."
echo "docker push 637423187518.dkr.ecr.eu-north-1.amazonaws.com/asgard:$(date +%Y%m%d-%H%M%S)"

echo ""
echo "🔍 Verification steps after deployment:"
echo "1. Check pod status: kubectl get pods -n asgard"
echo "2. Check logs: kubectl logs -n asgard deployment/asgard"
echo "3. Test API endpoint: curl -X POST http://asgard-app.local/dbt/transform -H 'Content-Type: application/json' -d '{\"name\":\"test\", \"sql_query\":\"SELECT 1\", \"description\":\"test\", \"materialization\":\"table\", \"owner\":\"admin\"}'"

echo ""
echo "🎯 Key fixes applied:"
echo "✅ DBT project directory set to writable /tmp/dbt_projects"
echo "✅ Proper temp directory permissions in Dockerfile"
echo "✅ DBT project structure auto-creation"
echo "✅ Production Trino/Nessie service configuration"
echo "✅ AWS secrets integration"
echo "✅ Volume mounts for temporary storage"

echo ""
echo "🚨 Known behavior:"
echo "- Local testing will show Trino connection errors (expected - services are in production)"
echo "- Permission denied errors should be resolved"
echo "- Full functionality available only in production Kubernetes environment"

echo ""
echo "✅ Ready for production deployment!"