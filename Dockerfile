# One image for the API, the worker and `dan`. The web app gets its own image (M6).
# uv 0.12.20 as in CI; Python 3.14.8 on Debian trixie.
FROM ghcr.io/astral-sh/uv:0.12.20 AS uv

FROM python:3.14.8-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependencies first, so a code change reuses this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
# The embedding model (64 MB) is downloaded here once, not on the server at first use.
RUN .venv/bin/python -c \
    "from dailyainotes.llm.embeddings import LocalEmbeddings; LocalEmbeddings('/app/models')"

FROM python:3.14.8-slim-trixie
RUN useradd --system --uid 10001 --home-dir /app dan
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build --chown=dan /app/models /app/models
COPY config ./config
# The eval set, for the worker's nightly run.
COPY evals ./evals
ENV PATH=/app/.venv/bin:$PATH EMBEDDING_CACHE_DIR=/app/models PYTHONUNBUFFERED=1
USER dan
EXPOSE 8000
# The worker runs `dan-worker`; `dan` runs one-off commands.
CMD ["uvicorn", "dailyainotes.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
