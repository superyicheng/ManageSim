#!/usr/bin/env bash
set -euo pipefail

echo "=== ManageSim Setup ==="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is required"
    exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
    echo "ERROR: node is required"
    exit 1
fi

echo "Installing Python dependencies..."
pip install -r pipeline/requirements.txt
pip install -r knowledge/requirements.txt
pip install -r asset_base/requirements.txt
pip install -r tools/requirements.txt 2>/dev/null || echo "  (tools/requirements.txt optional)"

echo "Installing Node dependencies..."
(cd gateway && npm install)
(cd evolution && npm install)
(cd orchestrator && npm install)

echo "Building TypeScript..."
(cd gateway && npm run build 2>/dev/null || echo "  gateway build skipped (run manually)")
(cd orchestrator && npm run build 2>/dev/null || echo "  orchestrator build skipped (run manually)")

# Create data directory
mkdir -p data

# Check for personal config
if [ ! -f config/managesim.yaml ]; then
    echo ""
    echo "No personal config found."
    echo "Run: ./scripts/init-personal.sh"
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. ./scripts/init-personal.sh   — create your personal config"
echo "  2. ./scripts/init-hierarchy.sh  — bootstrap Easybase tree"
echo "  3. docker-compose up            — start all services"
