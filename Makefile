.PHONY: help setup install dev test clean docker-up docker-down docker-logs docker-build docker-dev-up docker-dev-down docker-restart docker-ps docker-shell-surface docker-shell-inner docker-shell-crust

help:
	@echo "Insanity Cluster - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - Create virtual environment and install dependencies"
	@echo "  make install            - Install dependencies only"
	@echo ""
	@echo "Development:"
	@echo "  make dev                - Run development server locally"
	@echo "  make dev-surface        - Run SURFACE layer locally"
	@echo "  make demo-surface       - Run SURFACE layer demo"
	@echo "  make test               - Run tests"
	@echo "  make test-cov           - Run tests with coverage"
	@echo "  make lint               - Run linters"
	@echo "  make format             - Format code"
	@echo ""
	@echo "Docker - Production:"
	@echo "  make docker-build       - Build all Docker images"
	@echo "  make docker-up          - Start all services (production mode)"
	@echo "  make docker-down        - Stop all services"
	@echo "  make docker-restart     - Restart all services"
	@echo "  make docker-logs        - View service logs"
	@echo "  make docker-ps          - Show running containers"
	@echo "  make docker-clean       - Stop and remove all containers and volumes"
	@echo ""
	@echo "Docker - Development:"
	@echo "  make docker-dev-up      - Start all services (development mode with hot reload)"
	@echo "  make docker-dev-down    - Stop development services"
	@echo "  make docker-dev-logs    - View development service logs"
	@echo "  make docker-dev-build   - Rebuild development images"
	@echo ""
	@echo "Docker - Shell Access:"
	@echo "  make docker-shell-surface  - Open shell in SURFACE container"
	@echo "  make docker-shell-inner    - Open shell in INNER container"
	@echo "  make docker-shell-crust    - Open shell in CRUST container"
	@echo ""
	@echo "Database:"
	@echo "  make init-db            - Initialize database"
	@echo "  make migrate            - Run database migrations"
	@echo "  make migrate-create     - Create new migration"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Remove generated files"

setup:
	python scripts/setup_venv.py

install:
	pip install -r requirements.txt

dev:
	python -m insanity_cluster.surface.main

dev-surface:
	python -m insanity_cluster.surface.main

demo-surface:
	python examples/surface_layer_demo.py

test:
	pytest

test-cov:
	pytest --cov=insanity_cluster --cov-report=html --cov-report=term

lint:
	flake8 insanity_cluster tests
	mypy insanity_cluster

format:
	black insanity_cluster tests
	isort insanity_cluster tests

# Docker - Production
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-restart:
	docker-compose restart

docker-logs:
	docker-compose logs -f

docker-ps:
	docker-compose ps

docker-clean:
	docker-compose down -v --remove-orphans

# Docker - Development
docker-dev-build:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

docker-dev-up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

docker-dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

docker-dev-logs:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

docker-dev-restart:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

# Docker - Shell Access
docker-shell-surface:
	docker exec -it insanity_surface /bin/bash

docker-shell-inner:
	docker exec -it insanity_inner /bin/bash

docker-shell-crust:
	docker exec -it insanity_crust /bin/bash

docker-shell-postgres:
	docker exec -it insanity_postgres psql -U insanity -d insanity_cluster

docker-shell-redis:
	docker exec -it insanity_redis redis-cli

# Database
init-db:
	python scripts/init_database.py

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-downgrade:
	alembic downgrade -1

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
