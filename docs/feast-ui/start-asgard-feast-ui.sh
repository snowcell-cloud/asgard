#!/bin/bash

# Asgard Feast UI Launcher
# Sets up and launches Feast UI for the app/feast implementation

set -e

echo "🎯 Asgard Feast UI Setup & Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

FEAST_REPO="/tmp/feast_repo"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Check if setup is needed
if [ ! -f "$FEAST_REPO/feature_store.yaml" ]; then
    echo "📦 Setting up Feast repository for the first time..."
    echo ""
    
    # Run setup script from project directory
    cd "$SCRIPT_DIR"
    uv run python setup_feast_repo.py
    
    echo ""
    echo "✅ Initial setup complete!"
    echo ""
else
    echo "✅ Feast repository already configured at: $FEAST_REPO"
    echo ""
fi

# Step 2: Show current features
echo "📊 Current Features in Repository:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run feast commands from project directory with feast repo path
cd "$SCRIPT_DIR"

echo ""
echo "🔹 Feature Views:"
(cd "$FEAST_REPO" && "$SCRIPT_DIR/.venv/bin/feast" feature-views list) 2>/dev/null || echo "   No feature views registered"

echo ""
echo "🔹 Entities:"
(cd "$FEAST_REPO" && "$SCRIPT_DIR/.venv/bin/feast" entities list) 2>/dev/null || echo "   No entities registered"

echo ""
echo "🔹 Feature Services:"
(cd "$FEAST_REPO" && "$SCRIPT_DIR/.venv/bin/feast" feature-services list) 2>/dev/null || echo "   No feature services registered"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 3: Instructions for registering features via API
echo ""
echo "💡 To register features from your gold layer via API:"
echo ""
echo "   1. Start Asgard API (in another terminal):"
echo "      cd $SCRIPT_DIR"
echo "      uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "   2. Register features:"
echo '      curl -X POST http://localhost:8000/feast/features \'
echo '        -H "Content-Type: application/json" \'
echo '        -d '"'"'{'
echo '          "name": "your_feature_view",'
echo '          "entities": ["customer_id"],'
echo '          "features": ['
echo '            {"name": "feature_1", "dtype": "FLOAT64"},'
echo '            {"name": "feature_2", "dtype": "INT64"}'
echo '          ],'
echo '          "source": {'
echo '            "table_name": "your_table",'
echo '            "catalog": "iceberg",'
echo '            "schema": "gold"'
echo '          },'
echo '          "online": true'
echo '        }'"'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 4: Launch UI
HOST="${FEAST_UI_HOST:-0.0.0.0}"
PORT="${FEAST_UI_PORT:-8888}"

echo ""
echo "🌐 Starting Feast UI..."
echo ""
echo "   📍 Local:    http://localhost:${PORT}"
echo "   🔗 Network:  http://${HOST}:${PORT}"
echo ""
echo "   Press CTRL+C to stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Feast UI (must run from feast repo directory)
cd "$FEAST_REPO"
"$SCRIPT_DIR/.venv/bin/feast" ui -h "$HOST" -p "$PORT"
