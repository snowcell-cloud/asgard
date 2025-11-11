#!/bin/bash

# ============================================================================
# ML Model Deployment Pipeline
# ============================================================================
# This script automates the complete ML deployment workflow:
# 1. Train model using Feast features
# 2. Build Docker image
# 3. Push to AWS ECR
# 4. Deploy to EKS
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
AWS_REGION="${AWS_REGION:-eu-north-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-ml-inference}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
K8S_NAMESPACE="${K8S_NAMESPACE:-ml-inference}"
MODEL_NAME="${MODEL_NAME:-churn_predictor_feast}"
MLFLOW_URI="${MLFLOW_URI:-http://localhost:5000}"

# Derived variables
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URI}/${ECR_REPOSITORY}:${IMAGE_TAG}"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

check_requirements() {
    print_header "Checking Requirements"
    
    local missing=0
    
    # Check required tools
    for cmd in docker kubectl aws python3; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd is not installed"
            missing=1
        else
            print_success "$cmd is installed"
        fi
    done
    
    # Check AWS credentials
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_error "AWS_ACCOUNT_ID environment variable is not set"
        missing=1
    else
        print_success "AWS_ACCOUNT_ID is set"
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Missing requirements. Please install missing tools and set environment variables."
        exit 1
    fi
    
    echo ""
}

train_model() {
    print_header "Step 1: Training ML Model with Feast Features"
    
    # Check if port-forward to MLflow is active
    if ! curl -s "$MLFLOW_URI/health" > /dev/null 2>&1; then
        print_info "MLflow is not accessible at $MLFLOW_URI"
        print_info "Starting port-forward to MLflow..."
        kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &
        PF_PID=$!
        sleep 5
    fi
    
    # Set environment variables for training
    export MLFLOW_TRACKING_URI="$MLFLOW_URI"
    export MODEL_NAME="$MODEL_NAME"
    export EXPERIMENT_NAME="feast_ml_deployment"
    
    print_info "Training model: $MODEL_NAME"
    print_info "MLflow URI: $MLFLOW_TRACKING_URI"
    
    # Run training script
    if [ -f "ml_deployment/train_with_feast.py" ]; then
        python3 ml_deployment/train_with_feast.py
        
        if [ $? -eq 0 ]; then
            print_success "Model training completed successfully"
        else
            print_error "Model training failed"
            exit 1
        fi
    else
        print_error "Training script not found: ml_deployment/train_with_feast.py"
        exit 1
    fi
    
    # Kill port-forward if we started it
    if [ ! -z "$PF_PID" ]; then
        kill $PF_PID 2>/dev/null || true
    fi
    
    echo ""
}

build_docker_image() {
    print_header "Step 2: Building Docker Image"
    
    print_info "Building image: $FULL_IMAGE_NAME"
    
    # Build Docker image
    docker build \
        -f ml_deployment/Dockerfile.inference \
        -t "$FULL_IMAGE_NAME" \
        -t "${ECR_URI}/${ECR_REPOSITORY}:${MODEL_NAME}-${IMAGE_TAG}" \
        .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
        docker images | grep "$ECR_REPOSITORY" | head -5
    else
        print_error "Docker build failed"
        exit 1
    fi
    
    echo ""
}

push_to_ecr() {
    print_header "Step 3: Pushing Image to AWS ECR"
    
    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_URI"
    
    if [ $? -ne 0 ]; then
        print_error "ECR login failed"
        exit 1
    fi
    
    print_success "ECR login successful"
    
    # Create ECR repository if it doesn't exist
    print_info "Checking if ECR repository exists..."
    if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" > /dev/null 2>&1; then
        print_info "Creating ECR repository: $ECR_REPOSITORY"
        aws ecr create-repository \
            --repository-name "$ECR_REPOSITORY" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256
        
        print_success "ECR repository created"
    else
        print_success "ECR repository exists"
    fi
    
    # Push image
    print_info "Pushing image to ECR..."
    docker push "$FULL_IMAGE_NAME"
    
    if [ $? -eq 0 ]; then
        print_success "Image pushed successfully"
        print_info "Image URI: $FULL_IMAGE_NAME"
    else
        print_error "Image push failed"
        exit 1
    fi
    
    echo ""
}

deploy_to_eks() {
    print_header "Step 4: Deploying to EKS"
    
    # Update kubeconfig
    print_info "Updating kubeconfig..."
    aws eks update-kubeconfig --name asgard-cluster --region "$AWS_REGION" 2>/dev/null || true
    
    # Create namespace if it doesn't exist
    print_info "Creating namespace: $K8S_NAMESPACE"
    kubectl create namespace "$K8S_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Create AWS credentials secret
    print_info "Creating AWS credentials secret..."
    kubectl create secret generic aws-credentials \
        --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        --namespace="$K8S_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Update deployment manifest with image URI
    print_info "Updating deployment manifest..."
    sed -i.bak \
        "s|<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/ml-inference:latest|${FULL_IMAGE_NAME}|g" \
        ml_deployment/k8s/deployment.yaml
    
    # Apply Kubernetes manifests
    print_info "Applying Kubernetes manifests..."
    kubectl apply -f ml_deployment/k8s/deployment.yaml
    
    if [ $? -eq 0 ]; then
        print_success "Deployment applied successfully"
    else
        print_error "Deployment failed"
        exit 1
    fi
    
    # Restore original deployment file
    mv ml_deployment/k8s/deployment.yaml.bak ml_deployment/k8s/deployment.yaml
    
    # Wait for deployment to be ready
    print_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/ml-inference -n "$K8S_NAMESPACE" --timeout=5m
    
    if [ $? -eq 0 ]; then
        print_success "Deployment is ready"
    else
        print_error "Deployment rollout failed"
        exit 1
    fi
    
    echo ""
}

get_inference_url() {
    print_header "Step 5: Getting Inference URL"
    
    # Check if ingress is configured
    INGRESS_HOST=$(kubectl get ingress ml-inference-ingress -n "$K8S_NAMESPACE" -o jsonpath='{.spec.rules[0].host}' 2>/dev/null)
    
    if [ ! -z "$INGRESS_HOST" ]; then
        print_success "Ingress URL: https://$INGRESS_HOST"
        echo ""
        print_info "API Endpoints:"
        echo "  - Health:       https://$INGRESS_HOST/health"
        echo "  - Metadata:     https://$INGRESS_HOST/metadata"
        echo "  - Predict:      https://$INGRESS_HOST/predict"
        echo "  - Batch Predict: https://$INGRESS_HOST/batch_predict"
    else
        print_info "Ingress not configured. Use port-forward for local access:"
        echo ""
        echo "  kubectl port-forward -n $K8S_NAMESPACE svc/ml-inference-service 8080:80"
        echo ""
        print_info "Then access the API at: http://localhost:8080"
        echo ""
        print_info "API Endpoints:"
        echo "  - Health:       http://localhost:8080/health"
        echo "  - Metadata:     http://localhost:8080/metadata"
        echo "  - Predict:      http://localhost:8080/predict"
        echo "  - Batch Predict: http://localhost:8080/batch_predict"
    fi
    
    echo ""
    print_info "View deployment status:"
    echo "  kubectl get all -n $K8S_NAMESPACE"
    echo ""
    print_info "View logs:"
    echo "  kubectl logs -n $K8S_NAMESPACE -l app=ml-inference --tail=100 -f"
    
    echo ""
}

test_inference() {
    print_header "Step 6: Testing Inference Endpoint"
    
    # Start port-forward
    print_info "Starting port-forward for testing..."
    kubectl port-forward -n "$K8S_NAMESPACE" svc/ml-inference-service 8080:80 &
    PF_PID=$!
    sleep 5
    
    # Test health endpoint
    print_info "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
    
    if [ $? -eq 0 ]; then
        print_success "Health check passed"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool
    else
        print_error "Health check failed"
    fi
    
    echo ""
    
    # Test prediction endpoint
    print_info "Testing prediction endpoint..."
    PREDICT_PAYLOAD='{
      "inputs": {
        "total_purchases": [10, 25, 5],
        "avg_purchase_value": [50.0, 120.5, 30.0],
        "days_since_last_purchase": [5, 15, 200],
        "customer_lifetime_value": [500.0, 3000.0, 150.0],
        "account_age_days": [365, 730, 180],
        "support_tickets_count": [2, 1, 8]
      },
      "return_probabilities": true
    }'
    
    PREDICT_RESPONSE=$(curl -s -X POST http://localhost:8080/predict \
        -H "Content-Type: application/json" \
        -d "$PREDICT_PAYLOAD")
    
    if [ $? -eq 0 ]; then
        print_success "Prediction successful"
        echo "$PREDICT_RESPONSE" | python3 -m json.tool
    else
        print_error "Prediction failed"
    fi
    
    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
    
    echo ""
}

print_summary() {
    print_header "Deployment Summary"
    
    echo -e "${GREEN}✅ ML Model Deployment Completed Successfully!${NC}"
    echo ""
    echo "Deployment Details:"
    echo "  - Model Name:      $MODEL_NAME"
    echo "  - Image:           $FULL_IMAGE_NAME"
    echo "  - Namespace:       $K8S_NAMESPACE"
    echo "  - Replicas:        $(kubectl get deployment ml-inference -n $K8S_NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)"
    echo ""
    echo "Next Steps:"
    echo "  1. Configure your ingress hostname in ml_deployment/k8s/deployment.yaml"
    echo "  2. Set up DNS for your domain"
    echo "  3. Monitor logs: kubectl logs -n $K8S_NAMESPACE -l app=ml-inference -f"
    echo "  4. View metrics in MLflow: $MLFLOW_URI"
    echo ""
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    clear
    
    print_header "ML Model Deployment Pipeline"
    echo "  AWS Account: $AWS_ACCOUNT_ID"
    echo "  AWS Region:  $AWS_REGION"
    echo "  ECR Repo:    $ECR_REPOSITORY"
    echo "  Image Tag:   $IMAGE_TAG"
    echo "  Namespace:   $K8S_NAMESPACE"
    echo "  Model Name:  $MODEL_NAME"
    echo ""
    
    # Parse command line arguments
    SKIP_TRAIN=false
    SKIP_BUILD=false
    SKIP_PUSH=false
    SKIP_DEPLOY=false
    SKIP_TEST=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-train)
                SKIP_TRAIN=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --skip-deploy)
                SKIP_DEPLOY=true
                shift
                ;;
            --skip-test)
                SKIP_TEST=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-train   Skip model training"
                echo "  --skip-build   Skip Docker build"
                echo "  --skip-push    Skip ECR push"
                echo "  --skip-deploy  Skip EKS deployment"
                echo "  --skip-test    Skip inference testing"
                echo "  --help         Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute pipeline
    check_requirements
    
    [ "$SKIP_TRAIN" = false ] && train_model
    [ "$SKIP_BUILD" = false ] && build_docker_image
    [ "$SKIP_PUSH" = false ] && push_to_ecr
    [ "$SKIP_DEPLOY" = false ] && deploy_to_eks
    
    get_inference_url
    
    [ "$SKIP_TEST" = false ] && test_inference
    
    print_summary
}

# Run main function
main "$@"
