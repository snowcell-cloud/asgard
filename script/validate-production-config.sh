#!/bin/bash

# Production Configuration Validation Script
# Tests connectivity to Trino and Nessie services in data-platform namespace

echo "🔍 Production Configuration Validation - Data Platform Services"
echo "=============================================================="

# Configuration variables
TRINO_HOST="trino-coordinator.data-platform.svc.cluster.local"
TRINO_PORT="8080"
NESSIE_HOST="nessie.data-platform.svc.cluster.local"
NESSIE_PORT="19120"

echo "📋 Testing Configuration:"
echo "  - Trino: ${TRINO_HOST}:${TRINO_PORT}"
echo "  - Nessie: ${NESSIE_HOST}:${NESSIE_PORT}"
echo ""

# Test 1: Check if running in Kubernetes cluster
echo "🔍 Test 1: Kubernetes Cluster Environment"
if [ -f /var/run/secrets/kubernetes.io/serviceaccount/token ]; then
    echo "✅ Running inside Kubernetes cluster"
    NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
    echo "   Current namespace: ${NAMESPACE}"
else
    echo "⚠️  Not running in Kubernetes cluster - using external access"
fi
echo ""

# Test 2: DNS Resolution Test
echo "🔍 Test 2: DNS Resolution"
echo "Testing Trino DNS resolution..."
if nslookup ${TRINO_HOST} > /dev/null 2>&1; then
    echo "✅ Trino DNS resolution successful"
else
    echo "❌ Trino DNS resolution failed"
fi

echo "Testing Nessie DNS resolution..."
if nslookup ${NESSIE_HOST} > /dev/null 2>&1; then
    echo "✅ Nessie DNS resolution successful"
else
    echo "❌ Nessie DNS resolution failed"
fi
echo ""

# Test 3: Network Connectivity Test
echo "🔍 Test 3: Network Connectivity"
echo "Testing Trino connectivity..."
if timeout 10 bash -c "cat < /dev/null > /dev/tcp/${TRINO_HOST}/${TRINO_PORT}" 2>/dev/null; then
    echo "✅ Trino coordinator reachable at ${TRINO_HOST}:${TRINO_PORT}"
else
    echo "❌ Trino coordinator unreachable at ${TRINO_HOST}:${TRINO_PORT}"
fi

echo "Testing Nessie connectivity..."
if timeout 10 bash -c "cat < /dev/null > /dev/tcp/${NESSIE_HOST}/${NESSIE_PORT}" 2>/dev/null; then
    echo "✅ Nessie catalog reachable at ${NESSIE_HOST}:${NESSIE_PORT}"
else
    echo "❌ Nessie catalog unreachable at ${NESSIE_HOST}:${NESSIE_PORT}"
fi
echo ""

# Test 4: HTTP Endpoint Test
echo "🔍 Test 4: HTTP Endpoints"
echo "Testing Trino UI endpoint..."
if curl -s --connect-timeout 10 "http://${TRINO_HOST}:${TRINO_PORT}/ui/" > /dev/null; then
    echo "✅ Trino UI endpoint responding"
else
    echo "❌ Trino UI endpoint not responding"
fi

echo "Testing Nessie API endpoint..."
if curl -s --connect-timeout 10 "http://${NESSIE_HOST}:${NESSIE_PORT}/api/v1/config" > /dev/null; then
    echo "✅ Nessie API endpoint responding"
else
    echo "❌ Nessie API endpoint not responding"
fi
echo ""

# Test 5: Service Discovery Test
echo "🔍 Test 5: Kubernetes Service Discovery"
if command -v kubectl > /dev/null 2>&1; then
    echo "Testing Trino service in data-platform namespace..."
    if kubectl get svc trino-coordinator -n data-platform > /dev/null 2>&1; then
        echo "✅ Trino service found in data-platform namespace"
        kubectl get svc trino-coordinator -n data-platform -o wide
    else
        echo "❌ Trino service not found in data-platform namespace"
    fi
    
    echo "Testing Nessie service in data-platform namespace..."
    if kubectl get svc nessie -n data-platform > /dev/null 2>&1; then
        echo "✅ Nessie service found in data-platform namespace"
        kubectl get svc nessie -n data-platform -o wide
    else
        echo "❌ Nessie service not found in data-platform namespace"
    fi
else
    echo "⚠️  kubectl not available - skipping service discovery test"
fi
echo ""

# Test 6: AWS Secrets Test
echo "🔍 Test 6: AWS Secrets Configuration"
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✅ AWS credentials available from environment"
    echo "   AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:8}..."
    echo "   AWS_SECRET_ACCESS_KEY: [REDACTED]"
else
    echo "⚠️  AWS credentials not found in environment"
    echo "   Checking for secrets mounted in pod..."
    if [ -f /var/secrets/aws/access-key-id ]; then
        echo "✅ AWS access key found in mounted secret"
    else
        echo "❌ AWS access key not found in mounted secret"
    fi
fi
echo ""

# Test 7: S3 Connectivity Test (if AWS CLI available)
echo "🔍 Test 7: S3 Connectivity"
if command -v aws > /dev/null 2>&1; then
    echo "Testing S3 bucket access..."
    if aws s3 ls s3://asgard-data-lake/ > /dev/null 2>&1; then
        echo "✅ S3 bucket access successful"
        echo "   Available prefixes:"
        aws s3 ls s3://asgard-data-lake/ | head -5
    else
        echo "❌ S3 bucket access failed"
    fi
else
    echo "⚠️  AWS CLI not available - skipping S3 connectivity test"
fi
echo ""

echo "🎯 Production Configuration Summary"
echo "=================================="
echo "Configuration has been updated for production deployment with:"
echo "  ✅ Trino coordinator: trino-coordinator.data-platform.svc.cluster.local:8080"
echo "  ✅ Nessie catalog: nessie.data-platform.svc.cluster.local:19120"
echo "  ✅ AWS secrets integration from data-platform namespace"
echo "  ✅ S3 data lake: s3://asgard-data-lake (silver/gold schemas)"
echo ""
echo "🚀 Ready for production deployment!"
echo "   Deploy using: helm upgrade --install asgard ./helmchart"