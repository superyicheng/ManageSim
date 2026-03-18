#!/usr/bin/env bash
set -euo pipefail

echo "=== ManageSim Personal Configuration ==="

CONFIG_FILE="config/managesim.yaml"
ENV_FILE=".env"

# Copy template if no personal config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating personal config from template..."
    cp config/managesim.example.yaml "$CONFIG_FILE"
    echo "Created: $CONFIG_FILE"
    echo ""
    echo "Edit $CONFIG_FILE with your Discord Guild ID, Channel IDs, etc."
else
    echo "Personal config already exists: $CONFIG_FILE"
fi

# Copy .env template if not exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env from template..."
    cp .env.example "$ENV_FILE"
    echo "Created: $ENV_FILE"
    echo ""
    echo "Edit $ENV_FILE with your API keys and bot tokens."
else
    echo ".env already exists: $ENV_FILE"
fi

# Create data directory
mkdir -p data

echo ""
echo "=== Personal config initialized ==="
echo ""
echo "Next steps:"
echo "  1. Edit config/managesim.yaml with your Discord IDs"
echo "  2. Edit .env with your API keys and bot tokens"
echo "  3. Run: ./scripts/init-hierarchy.sh"
