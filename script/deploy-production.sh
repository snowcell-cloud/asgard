#!/bin/bash

# Production deployment script for Data Products API

set -e

echo "🚀 Deploying Data Products API to Production Environment"
echo "========================================================"

# Configuration
NAMESPACE="asgard"
APP_NAME="asgard-data-products-api"
CONFIGMAP_NAME="asgard-app-code"

# Function to check if namespace exists
check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        echo "📁 Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    else
        echo "✅ Namespace $NAMESPACE already exists"
    fi
}

# Function to create/update ConfigMap with application code
update_configmap() {
    echo "📦 Updating ConfigMap with application code..."
    
    # Create temporary directory for clean code
    TEMP_DIR=$(mktemp -d)
    
    # Copy only necessary files
    mkdir -p "$TEMP_DIR/app"
    cp -r app/* "$TEMP_DIR/app/"
    cp -r dbt "$TEMP_DIR/"
    cp pyproject.toml "$TEMP_DIR/"
    
    # Remove __pycache__ directories
    find "$TEMP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Create ConfigMap
    kubectl create configmap "$CONFIGMAP_NAME" \
        --from-file="$TEMP_DIR" \
        --dry-run=client -o yaml | kubectl apply -f - -n "$NAMESPACE"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    echo "✅ ConfigMap updated successfully"
}

# Function to deploy the application
deploy_application() {
    echo "🚢 Deploying application..."
    
    # Apply the production deployment
    kubectl apply -f k8s/production-deployment.yaml
    
    echo "⏳ Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/"$APP_NAME" -n "$NAMESPACE"
    
    echo "✅ Deployment ready!"
}

# Function to check deployment status
check_status() {
    echo "📊 Checking deployment status..."
    
    echo ""
    echo "Pods:"
    kubectl get pods -l app="$APP_NAME" -n "$NAMESPACE"
    
    echo ""
    echo "Services:"
    kubectl get svc "$APP_NAME" -n "$NAMESPACE"
    
    echo ""
    echo "Ingress:"
    kubectl get ingress "$APP_NAME" -n "$NAMESPACE" 2>/dev/null || echo "No ingress configured"
}

# Function to test the deployment
test_deployment() {
    echo "🧪 Testing deployment..."
    
    # Port forward for testing
    echo "Setting up port-forward for testing..."
    kubectl port-forward -n "$NAMESPACE" svc/"$APP_NAME" 8000:8000 &
    PORT_FORWARD_PID=$!
    
    # Wait for port-forward to be ready
    sleep 5
    
    # Test health endpoint
    echo "Testing health endpoint..."
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo "✅ Health check passed"
    else
        echo "❌ Health check failed"
    fi
    
    # Test API endpoints
    echo "Testing API endpoints..."
    if curl -s http://localhost:8000/api/v1/data-products/ | grep -q "data_products"; then
        echo "✅ API endpoints accessible"
    else
        echo "❌ API endpoints not accessible"
    fi
    
    # Cleanup port-forward
    kill $PORT_FORWARD_PID 2>/dev/null || true
}

# Function to show access information
show_access_info() {
    echo ""
    echo "🌐 Access Information"
    echo "===================="
    
    # Get service information
    SERVICE_IP=$(kubectl get svc "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    SERVICE_PORT=$(kubectl get svc "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    echo "Internal Service: http://$SERVICE_IP:$SERVICE_PORT"
    echo ""
    echo "To access from outside the cluster:"
    echo "kubectl port-forward -n $NAMESPACE svc/$APP_NAME 8000:8000"
    echo "Then visit: http://localhost:8000"
    echo ""
    echo "API Documentation: http://localhost:8000/docs"
    echo "Health Check: http://localhost:8000/health"
    echo ""
    
    # Check if ingress is configured
    if kubectl get ingress "$APP_NAME" -n "$NAMESPACE" &> /dev/null; then
        INGRESS_HOST=$(kubectl get ingress "$APP_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.rules[0].host}')
        echo "Ingress URL: http://$INGRESS_HOST"
        echo "Note: Make sure your ingress controller is configured and DNS is set up"
    fi
}

# Function to show logs
show_logs() {
    echo ""
    echo "📋 Recent logs:"
    kubectl logs -l app="$APP_NAME" -n "$NAMESPACE" --tail=20
}

# Main execution
main() {
    echo "Starting production deployment..."
    
    check_namespace
    update_configmap
    deploy_application
    check_status
    test_deployment
    show_access_info
    show_logs
    
    echo ""
    echo "🎉 Production deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Test the API endpoints"
    echo "2. Create test data products"
    echo "3. Verify gold layer transformations"
    echo "4. Set up monitoring and alerting"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        check_status
        ;;
    "test")
        test_deployment
        ;;
    "logs")
        kubectl logs -f -l app="$APP_NAME" -n "$NAMESPACE"
        ;;
    "delete")
        echo "🗑️  Deleting deployment..."
        kubectl delete -f k8s/production-deployment.yaml
        kubectl delete configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" || true
        echo "✅ Deployment deleted"
        ;;
    *)
        echo "Usage: $0 [deploy|status|test|logs|delete]"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the application (default)"
        echo "  status  - Check deployment status"
        echo "  test    - Test the deployment"
        echo "  logs    - Show application logs"
        echo "  delete  - Delete the deployment"
        exit 1
        ;;
esac