#!/bin/bash
set -e

echo "🎨 Feast UI - Quick Start Script"
echo "================================"
echo ""

# Configuration
FEAST_REPO_PATH=${FEAST_REPO_PATH:-/tmp/feast_repo}
UI_HOST=${FEAST_UI_HOST:-0.0.0.0}
UI_PORT=${FEAST_UI_PORT:-8888}

echo "📋 Configuration:"
echo "   Feast Repo: $FEAST_REPO_PATH"
echo "   UI Host: $UI_HOST"
echo "   UI Port: $UI_PORT"
echo ""

# Check if feast repo exists
if [ ! -d "$FEAST_REPO_PATH" ]; then
    echo "⚠️  Feast repository not found at $FEAST_REPO_PATH"
    echo "   Creating directory..."
    mkdir -p "$FEAST_REPO_PATH"
fi

# Check for feature_store.yaml
if [ ! -f "$FEAST_REPO_PATH/feature_store.yaml" ]; then
    echo "⚠️  No feature_store.yaml found"
    echo "   Creating default configuration..."
    
    cat > "$FEAST_REPO_PATH/feature_store.yaml" <<EOF
project: asgard_features
registry: $FEAST_REPO_PATH/registry.db
provider: local
online_store:
    type: sqlite
    path: $FEAST_REPO_PATH/online_store.db
offline_store:
    type: trino
    host: ${TRINO_HOST:-trino.data-platform.svc.cluster.local}
    port: ${TRINO_PORT:-8080}
    catalog: ${TRINO_CATALOG:-iceberg}
    connector:
        type: iceberg
entity_key_serialization_version: 2
EOF
    
    echo "✅ Created feature_store.yaml"
fi

# Navigate to feast repo
cd "$FEAST_REPO_PATH" || exit 1

echo ""
echo "📦 Checking Feast installation..."
if ! uv run feast --version > /dev/null 2>&1; then
    echo "❌ Feast not found!"
    echo "   Please install with: uv add feast[ui]"
    exit 1
fi

echo "✅ Feast installed: $(uv run feast --version)"

# Apply features (if registry exists)
if [ -f "$FEAST_REPO_PATH/registry.db" ]; then
    echo ""
    echo "📦 Applying features to registry..."
    uv run feast apply || echo "⚠️  No features to apply (this is normal for first run)"
fi

echo ""
echo "🚀 Starting Feast UI..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Feast UI will be available at:"
echo "   http://localhost:$UI_PORT"
echo ""
echo "📚 To use the UI:"
echo "   1. Open browser to http://localhost:$UI_PORT"
echo "   2. Browse Feature Views, Entities, and Data Sources"
echo "   3. Register features first via Asgard API if empty"
echo ""
echo "🛑 Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Feast UI
uv run feast ui -h "$UI_HOST" -p "$UI_PORT"
