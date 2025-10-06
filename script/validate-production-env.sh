#!/bin/bash

# Production Environment Validation for DBT Transformations API
# This script validates that all required components are properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Production Environment Validation${NC}"
echo "===================================="

# Check counter
CHECKS_PASSED=0
CHECKS_FAILED=0

# Function to run validation check
validate() {
    local check_name="$1"
    local check_command="$2"
    local required="${3:-true}"
    
    echo -e "\n${BLUE}Checking: ${check_name}${NC}"
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED: ${check_name}${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ FAILED: ${check_name}${NC}"
            ((CHECKS_FAILED++))
        else
            echo -e "${YELLOW}⚠️  OPTIONAL: ${check_name}${NC}"
        fi
        return 1
    fi
}

# Core System Checks
echo -e "\n${BLUE}1. Core System Components${NC}"

validate "Python 3.8+ installed" "python3 --version | grep -E 'Python 3\.([8-9]|[1-9][0-9])'"
validate "dbt Core installed" "dbt --version"
validate "curl available" "which curl"
validate "jq available" "which jq"

# Directory Structure Checks
echo -e "\n${BLUE}2. Directory Structure${NC}"

DBT_PROJECT_DIR="${DBT_PROJECT_DIR:-/home/hac/downloads/code/asgard-dev/dbt}"
validate "dbt project directory exists" "test -d '$DBT_PROJECT_DIR'"
validate "dbt models directory exists" "test -d '$DBT_PROJECT_DIR/models'"
validate "dbt gold models directory exists" "test -d '$DBT_PROJECT_DIR/models/gold'" false

# dbt Configuration Checks
echo -e "\n${BLUE}3. dbt Configuration${NC}"

validate "dbt_project.yml exists" "test -f '$DBT_PROJECT_DIR/dbt_project.yml'"
validate "profiles.yml exists" "test -f '$DBT_PROJECT_DIR/profiles.yml' || test -f ~/.dbt/profiles.yml"

# Check if we can parse dbt project
if validate "dbt project parses correctly" "cd '$DBT_PROJECT_DIR' && dbt parse --profiles-dir ." false; then
    echo "  dbt project configuration is valid"
else
    echo "  Note: dbt parse failed - check profiles.yml configuration"
fi

# Environment Variables Check
echo -e "\n${BLUE}4. Environment Variables${NC}"

# Required variables
ENV_VARS=(
    "TRINO_HOST:Trino host configuration"
    "TRINO_PORT:Trino port configuration"
    "TRINO_CATALOG:Trino catalog name"
    "SILVER_SCHEMA:Silver layer schema name"
    "GOLD_SCHEMA:Gold layer schema name"
)

for var_config in "${ENV_VARS[@]}"; do
    IFS=':' read -r var_name var_desc <<< "$var_config"
    if [ ! -z "${!var_name}" ]; then
        echo -e "${GREEN}✅ ${var_desc}: ${!var_name}${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠️  ${var_desc}: Not set (using default)${NC}"
    fi
done

# Network Connectivity Checks
echo -e "\n${BLUE}5. Network Connectivity${NC}"

TRINO_HOST=${TRINO_HOST:-localhost}
TRINO_PORT=${TRINO_PORT:-8080}

validate "Trino connectivity" "nc -z '$TRINO_HOST' '$TRINO_PORT'" false

# Application Checks
echo -e "\n${BLUE}6. Application Status${NC}"

API_URL="${API_BASE_URL:-http://localhost:8000}"
validate "Application health endpoint" "curl -s --max-time 5 '$API_URL/health'"
validate "DBT transformations endpoint" "curl -s --max-time 5 '$API_URL/api/v1/dbt-transformations/health'"

# Configuration File Validation
echo -e "\n${BLUE}7. Configuration Files${NC}"

# Check profiles.yml content
PROFILES_FILE="$DBT_PROJECT_DIR/profiles.yml"
if [ -f "$PROFILES_FILE" ]; then
    validate "profiles.yml has trino connection" "grep -q 'type: trino' '$PROFILES_FILE'"
    validate "profiles.yml has host configuration" "grep -q 'host:' '$PROFILES_FILE'"
    validate "profiles.yml has catalog configuration" "grep -q 'catalog:' '$PROFILES_FILE'"
else
    echo -e "${YELLOW}⚠️  profiles.yml not found in project directory${NC}"
fi

# Check dbt_project.yml content
DBT_PROJECT_FILE="$DBT_PROJECT_DIR/dbt_project.yml"
if [ -f "$DBT_PROJECT_FILE" ]; then
    validate "dbt_project.yml has models configuration" "grep -q 'models:' '$DBT_PROJECT_FILE'"
    validate "dbt project name configured" "grep -q 'name:' '$DBT_PROJECT_FILE'"
else
    echo -e "${RED}❌ dbt_project.yml not found${NC}"
    ((CHECKS_FAILED++))
fi

# S3/Storage Checks (if configured)
echo -e "\n${BLUE}8. Storage Configuration${NC}"

if [ ! -z "$S3_BUCKET" ]; then
    validate "AWS CLI available" "which aws" false
    if which aws > /dev/null 2>&1; then
        validate "S3 bucket accessible" "aws s3 ls 's3://$S3_BUCKET/' --max-items 1" false
    fi
else
    echo -e "${YELLOW}⚠️  S3_BUCKET not configured - using default storage${NC}"
fi

# Security Checks
echo -e "\n${BLUE}9. Security Configuration${NC}"

# Check for sensitive files
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file found for configuration${NC}"
    ((CHECKS_PASSED++))
    
    # Check if .env is in .gitignore
    if [ -f ".gitignore" ] && grep -q "\.env" .gitignore; then
        echo -e "${GREEN}✅ .env file is in .gitignore${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}❌ .env file should be in .gitignore${NC}"
        ((CHECKS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found - using environment variables${NC}"
fi

# Performance Checks
echo -e "\n${BLUE}10. Performance Validation${NC}"

# Check API response time
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    start_time=$(date +%s%N)
    curl -s "$API_URL/api/v1/dbt-transformations/health" > /dev/null
    end_time=$(date +%s%N)
    response_time=$(( (end_time - start_time) / 1000000 ))
    
    if [ $response_time -lt 1000 ]; then
        echo -e "${GREEN}✅ API response time: ${response_time}ms${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠️  API response time slow: ${response_time}ms${NC}"
    fi
else
    echo -e "${RED}❌ API not responding${NC}"
    ((CHECKS_FAILED++))
fi

# Final Summary
echo -e "\n${BLUE}📊 Validation Summary${NC}"
echo "===================="
echo -e "Checks Passed: ${GREEN}${CHECKS_PASSED}${NC}"
echo -e "Checks Failed: ${RED}${CHECKS_FAILED}${NC}"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 Environment validation passed! Ready for production testing.${NC}"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "1. Run: ./production-test-dbt-api.sh"
    echo "2. Monitor logs during testing"
    echo "3. Verify transformations in your data lake"
    
    exit 0
else
    echo -e "\n${RED}❌ Environment validation failed. Please fix the issues above.${NC}"
    
    echo -e "\n${BLUE}Common fixes:${NC}"
    echo "• Install missing dependencies (dbt, python packages)"
    echo "• Configure dbt profiles.yml with Trino connection"
    echo "• Set required environment variables"
    echo "• Ensure Trino cluster is accessible"
    echo "• Check network connectivity"
    
    exit 1
fi