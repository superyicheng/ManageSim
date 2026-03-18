#!/usr/bin/env bash
set -euo pipefail

echo "=== ManageSim Hierarchy Initialization ==="

CONFIG_FILE="${1:-config/managesim.yaml}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    echo "Run ./scripts/init-personal.sh first."
    exit 1
fi

echo "Bootstrapping Easybase tree from: $CONFIG_FILE"

# Run the hierarchy init script
python3 -c "
import yaml
import sys
sys.path.insert(0, '.')
from knowledge.easybase_bridge import EasybaseBridge
from knowledge.hierarchy_init import init_full_hierarchy

with open('$CONFIG_FILE') as f:
    config = yaml.safe_load(f)

bridge = EasybaseBridge()
init_full_hierarchy(bridge, config)
print('Hierarchy initialized successfully!')
print('Server soul.md and project souls created in Easybase.')
"

echo ""
echo "=== Hierarchy initialized ==="
echo "Run: docker-compose up"
