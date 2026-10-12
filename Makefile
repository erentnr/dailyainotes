# The gate before every commit is `make check` (INTENT.md, Testing Requirements).

.PHONY: check lint types test fmt up down api

check: lint types test

# Postgres for development and integration tests (docker-compose.yml).
up:
	docker compose up -d --wait db

down:
	docker compose down

# The API on http://localhost:8000, reloading on code changes.
api:
	uv run --frozen uvicorn dailyainotes.api.app:create_app --factory --reload --port 8000

lint:
	uv run --frozen ruff format --check .
	uv run --frozen ruff check .

types:
	uv run --frozen mypy

test:
	uv run --frozen pytest

fmt:
	uv run --frozen ruff format .
	uv run --frozen ruff check --fix .
