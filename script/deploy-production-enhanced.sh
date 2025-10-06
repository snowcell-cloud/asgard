#!/bin/bash

# Enhanced Production deployment script for Asgard Data Platform with DBT Transformations API

set -e

echo "🚀 Deploying Asgard Data Platform with DBT Transformations API to Production"
echo "==========================================================================="

# Configuration
NAMESPACE="asgard"
APP_NAME="asgard-data-platform-api"
CONFIGMAP_NAME="asgard-app-code"
DBT_CONFIGMAP_NAME="asgard-dbt-config"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEPLOYMENT_LOG="deployment_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "$1" | tee -a "${DEPLOYMENT_LOG}"
}

# Function to check if namespace exists
check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log "📁 Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    else
        log "📁 Using existing namespace: $NAMESPACE"
    fi
}

# Function to validate environment
validate_environment() {
    log "\n${BLUE}🔍 Validating Production Environment${NC}"
    
    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log "${RED}❌ kubectl not connected to cluster${NC}"
        exit 1
    fi
    
    # Check required files
    local required_files=(
        "app/main.py"
        "app/dbt_transformations/router.py"
        "app/dbt_transformations/service.py"
        "app/dbt_transformations/schemas.py"
        "dbt/dbt_project.yml"
        "k8s/production-deployment.yaml"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "${RED}❌ Required file not found: $file${NC}"
            exit 1
        fi
    done
    
    log "${GREEN}✅ Environment validation passed${NC}"
}

# Function to create or update ConfigMaps
update_configmaps() {
    log "\n${BLUE}📋 Updating ConfigMaps${NC}"
    
    # Update main application code ConfigMap
    if kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" &> /dev/null; then
        log "Updating existing ConfigMap: $CONFIGMAP_NAME"
        kubectl delete configmap "$CONFIGMAP_NAME" -n "$NAMESPACE"
    fi
    
    log "Creating ConfigMap with application code..."
    kubectl create configmap "$CONFIGMAP_NAME" \
        --from-file=app/ \
        --from-file=pyproject.toml \
        --from-file=requirements.txt \
        -n "$NAMESPACE"
    
    # Create/update DBT configuration ConfigMap
    if kubectl get configmap "$DBT_CONFIGMAP_NAME" -n "$NAMESPACE" &> /dev/null; then
        log "Updating existing DBT ConfigMap: $DBT_CONFIGMAP_NAME"
        kubectl delete configmap "$DBT_CONFIGMAP_NAME" -n "$NAMESPACE"
    fi
    
    log "Creating DBT configuration ConfigMap..."
    kubectl create configmap "$DBT_CONFIGMAP_NAME" \
        --from-file=dbt/ \
        -n "$NAMESPACE"
    
    log "${GREEN}✅ ConfigMaps updated successfully${NC}"
}

# Function to create production secrets
create_secrets() {
    log "\n${BLUE}🔐 Managing Production Secrets${NC}"
    
    # Check if secrets exist
    if ! kubectl get secret "asgard-secrets" -n "$NAMESPACE" &> /dev/null; then
        log "Creating production secrets..."
        
        # Create secret with default values (replace with actual values)
        kubectl create secret generic "asgard-secrets" \
            --from-literal=TRINO_HOST="${TRINO_HOST:-trino.asgard.svc.cluster.local}" \
            --from-literal=TRINO_PORT="${TRINO_PORT:-8080}" \
            --from-literal=TRINO_USER="${TRINO_USER:-trino}" \
            --from-literal=TRINO_CATALOG="${TRINO_CATALOG:-iceberg}" \
            --from-literal=SILVER_SCHEMA="${SILVER_SCHEMA:-silver}" \
            --from-literal=GOLD_SCHEMA="${GOLD_SCHEMA:-gold}" \
            --from-literal=S3_BUCKET="${S3_BUCKET:-asgard-data-lake}" \
            --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
            --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
            --from-literal=NESSIE_URI="${NESSIE_URI:-http://nessie.asgard.svc.cluster.local:19120/api/v1}" \
            -n "$NAMESPACE"
    else
        log "Production secrets already exist"
    fi
    
    log "${GREEN}✅ Secrets configured${NC}"
}

# Function to deploy application
deploy_application() {
    log "\n${BLUE}🚀 Deploying Application${NC}"
    
    # Apply the deployment
    if [ -f "k8s/production-deployment.yaml" ]; then
        log "Applying production deployment..."
        envsubst < k8s/production-deployment.yaml | kubectl apply -n "$NAMESPACE" -f -
    else
        log "${YELLOW}⚠️  production-deployment.yaml not found, creating basic deployment${NC}"
        create_basic_deployment
    fi
    
    # Wait for deployment to be ready
    log "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/"$APP_NAME" -n "$NAMESPACE"
    
    log "${GREEN}✅ Application deployed successfully${NC}"
}

# Function to create basic deployment if k8s config doesn't exist
create_basic_deployment() {
    cat << EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP_NAME
  labels:
    app: $APP_NAME
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $APP_NAME
  template:
    metadata:
      labels:
        app: $APP_NAME
    spec:
      containers:
      - name: api
        image: python:3.11-slim
        ports:
        - containerPort: 8000
        env:
        - name: DBT_PROJECT_DIR
          value: "/app/dbt"
        envFrom:
        - secretRef:
            name: asgard-secrets
        command: ["sh", "-c"]
        args:
        - |
          pip install -r /app/requirements.txt
          cd /app && python -m app.main
        volumeMounts:
        - name: app-code
          mountPath: /app
        - name: dbt-config
          mountPath: /app/dbt
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: app-code
        configMap:
          name: $CONFIGMAP_NAME
      - name: dbt-config
        configMap:
          name: $DBT_CONFIGMAP_NAME
---
apiVersion: v1
kind: Service
metadata:
  name: $APP_NAME
spec:
  selector:
    app: $APP_NAME
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
EOF
}

# Function to run post-deployment tests
run_post_deployment_tests() {
    log "\n${BLUE}🧪 Running Post-Deployment Tests${NC}"
    
    # Get service endpoint
    SERVICE_IP=$(kubectl get service "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    # Port forward for testing
    log "Setting up port forwarding for testing..."
    kubectl port-forward service/"$APP_NAME" 8080:80 -n "$NAMESPACE" &
    PORT_FORWARD_PID=$!
    
    # Wait for port forward to be ready
    sleep 10
    
    # Test endpoints
    local test_endpoints=(
        "http://localhost:8080/health"
        "http://localhost:8080/api/v1/dbt-transformations/health"
        "http://localhost:8080/api/v1/dbt-transformations/sources/silver"
    )
    
    for endpoint in "${test_endpoints[@]}"; do
        log "Testing endpoint: $endpoint"
        if curl -s --max-time 10 "$endpoint" > /dev/null; then
            log "${GREEN}✅ $endpoint - OK${NC}"
        else
            log "${RED}❌ $endpoint - Failed${NC}"
        fi
    done
    
    # Stop port forward
    kill $PORT_FORWARD_PID 2>/dev/null || true
    
    log "${GREEN}✅ Post-deployment tests completed${NC}"
}

# Function to display deployment status
show_deployment_status() {
    log "\n${BLUE}📊 Deployment Status${NC}"
    
    echo "Deployment Details:"
    kubectl get deployment "$APP_NAME" -n "$NAMESPACE"
    
    echo -e "\nPod Status:"
    kubectl get pods -l app="$APP_NAME" -n "$NAMESPACE"
    
    echo -e "\nService Details:"
    kubectl get service "$APP_NAME" -n "$NAMESPACE"
    
    echo -e "\nConfigMaps:"
    kubectl get configmaps -n "$NAMESPACE" | grep asgard
    
    echo -e "\nSecrets:"
    kubectl get secrets -n "$NAMESPACE" | grep asgard
}

# Function to create monitoring and alerting
setup_monitoring() {
    log "\n${BLUE}📈 Setting up Monitoring${NC}"
    
    # Create ServiceMonitor for Prometheus (if using Prometheus Operator)
    cat << EOF | kubectl apply -n "$NAMESPACE" -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: $APP_NAME-monitor
  labels:
    app: $APP_NAME
spec:
  selector:
    matchLabels:
      app: $APP_NAME
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
EOF
    
    log "${GREEN}✅ Monitoring configured${NC}"
}

# Main deployment flow
main() {
    log "Starting deployment at $(date)"
    
    # Pre-deployment validation
    validate_environment
    
    # Setup namespace
    check_namespace
    
    # Create/update ConfigMaps
    update_configmaps
    
    # Create secrets
    create_secrets
    
    # Deploy application
    deploy_application
    
    # Setup monitoring
    setup_monitoring || log "${YELLOW}⚠️  Monitoring setup failed (optional)${NC}"
    
    # Run tests
    run_post_deployment_tests
    
    # Show status
    show_deployment_status
    
    log "\n${GREEN}🎉 Deployment completed successfully!${NC}"
    log "Application is available at:"
    log "• Internal: http://$APP_NAME.$NAMESPACE.svc.cluster.local"
    log "• Port forward: kubectl port-forward service/$APP_NAME 8080:80 -n $NAMESPACE"
    log "• API docs: http://localhost:8080/docs (after port forward)"
    
    log "\n${BLUE}Next Steps:${NC}"
    log "1. Run comprehensive tests: ./production-test-dbt-api.sh"
    log "2. Configure external ingress/load balancer"
    log "3. Setup monitoring dashboards"
    log "4. Configure backup and disaster recovery"
    
    log "\nDeployment log saved to: $DEPLOYMENT_LOG"
}

# Run main function
main "$@"