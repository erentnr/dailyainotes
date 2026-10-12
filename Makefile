# The gate before every commit is `make check` (INTENT.md, Testing Requirements).

.PHONY: check lint types test fmt

check: lint types test

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
