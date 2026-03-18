.PHONY: setup dev test health clean docker-up docker-down init-personal init-hierarchy

# Full setup
setup:
	./scripts/setup.sh

# Development setup (no Docker)
dev:
	pip install -r pipeline/requirements.txt
	pip install -r knowledge/requirements.txt
	pip install -r asset_base/requirements.txt
	cd gateway && npm install
	cd evolution && npm install
	cd orchestrator && npm install

# Run tests
test:
	python3 -m pytest pipeline/ -v
	python3 -m pytest knowledge/ -v
	python3 -m pytest asset_base/ -v

# Health check
health:
	python3 scripts/health-check.py

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf data/*.db

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Personalization
init-personal:
	./scripts/init-personal.sh

init-hierarchy:
	./scripts/init-hierarchy.sh
