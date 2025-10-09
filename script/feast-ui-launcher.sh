#!/bin/bash

# Quick Feast UI Launcher
# Choose which Feast UI to view

echo "🎯 Feast UI Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Which Feast UI would you like to view?"
echo ""
echo "1) Pro Hawk Demo (local Parquet example)"
echo "2) Asgard Feast (Trino + Iceberg integration)"
echo "3) Both (different ports)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
  1)
    echo ""
    echo "🚀 Starting Pro Hawk Demo UI..."
    cd /home/hac/downloads/code/asgard-dev/pro_hawk/feature_repo
    echo "📂 Location: $(pwd)"
    echo "🌐 URL: http://localhost:8888"
    echo ""
    uv run feast apply
    echo ""
    uv run feast ui -h 0.0.0.0 -p 8888
    ;;
  2)
    echo ""
    echo "🚀 Starting Asgard Feast UI..."
    cd /tmp/feast_repo
    
    # Create directory if not exists
    if [ ! -d "/tmp/feast_repo" ]; then
      mkdir -p /tmp/feast_repo/data
    fi
    
    # Create feature_store.yaml if not exists
    if [ ! -f "feature_store.yaml" ]; then
      cat > feature_store.yaml << 'EOF'
project: asgard_feast
registry: /tmp/feast_repo/data/registry.db
provider: local
online_store:
    type: sqlite
    path: /tmp/feast_repo/data/online_store.db
entity_key_serialization_version: 3
auth:
    type: no_auth
EOF
    fi
    
    echo "📂 Location: $(pwd)"
    echo "🌐 URL: http://localhost:8888"
    echo ""
    echo "ℹ️  Note: Register features via Asgard API first:"
    echo "   POST http://localhost:8000/feast/features"
    echo ""
    uv run feast feature-views list || echo "No features registered yet"
    echo ""
    uv run feast ui -h 0.0.0.0 -p 8888
    ;;
  3)
    echo ""
    echo "🚀 Starting Both UIs..."
    echo ""
    echo "Starting Pro Hawk on port 8888..."
    cd /home/hac/downloads/code/asgard-dev/pro_hawk/feature_repo
    uv run feast apply
    uv run feast ui -h 0.0.0.0 -p 8888 &
    PID1=$!
    
    echo ""
    echo "Starting Asgard Feast on port 8889..."
    cd /tmp/feast_repo
    
    # Create directory if not exists
    if [ ! -d "/tmp/feast_repo" ]; then
      mkdir -p /tmp/feast_repo/data
    fi
    
    # Create feature_store.yaml if not exists
    if [ ! -f "feature_store.yaml" ]; then
      cat > feature_store.yaml << 'EOF'
project: asgard_feast
registry: /tmp/feast_repo/data/registry.db
provider: local
online_store:
    type: sqlite
    path: /tmp/feast_repo/data/online_store.db
entity_key_serialization_version: 3
auth:
    type: no_auth
EOF
    fi
    
    uv run feast ui -h 0.0.0.0 -p 8889 &
    PID2=$!
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Both UIs Running!"
    echo ""
    echo "📊 Pro Hawk Demo:    http://localhost:8888"
    echo "🚀 Asgard Feast:     http://localhost:8889"
    echo ""
    echo "Press CTRL+C to stop both"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Wait for both processes
    wait $PID1 $PID2
    ;;
  *)
    echo "Invalid choice"
    exit 1
    ;;
esac
