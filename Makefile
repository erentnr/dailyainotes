# The gate before every commit is `make check` (INTENT.md, Testing Requirements).

.PHONY: check lint types test fmt up down api api-types web-check readme-media

check: lint types test web-check

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

# The site's API types, from FastAPI's OpenAPI schema (never edit web/src/lib/api/ by hand).
api-types:
	uv run --frozen python -c "import json; from dailyainotes.api.app import create_app; from dailyainotes.settings import Settings; print(json.dumps(create_app(Settings(_env_file=None)).openapi(), indent=1))" > web/openapi.json
	cd web && npx --yes pnpm@12.8.1 run api-types

# The site's checks: astro check (types) and vitest. `cd web && npx --yes pnpm@12.8.1 install` first.
web-check:
	cd web && npx --yes pnpm@12.8.1 run check

# The README's pictures, taken from the live site (needs ffmpeg and ImageMagick 7).
readme-media:
	web/e2e/readme-media.sh
