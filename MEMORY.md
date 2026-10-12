# MEMORY.md: Agent Memory

Persistent memory for AI agents working on Daily AI Notes, modeled on agentmemory's pipeline of observations, compression, and tiered consolidation (github.com/rohitg00/agentmemory). It serves the development process only.

**Convention:** read this file at session start (AGENTS.md sends every agent here; Claude Code loads it through AGENTS.md's import); the Semantic and Procedural tiers are ground truth. This file is public. Its private counterpart, `.private/MEMORY.md`, is gitignored and holds what INTENT.md's Project Memory section lists as private. At session end: append dated observations to Episodic, promote durable knowledge into Semantic/Procedural, and keep Working Memory to the 3–5 lines that describe now. One line per memory, prefixed `[YYYY-MM-DD]`, tagged `#decision` `#insight` `#bug` `#preference` `#fact` `#event`. At each consolidation, every Episodic entry is promoted or deleted; the full pre-consolidation log lives in git. Rules belong in INTENT.md, not here.

Started 2026-10-12; no consolidation yet.

## Working Memory

- **[2026-10-12] Planned and approved; nothing is built yet.** Next is M0 Foundations, done when `make up && make check` pass, `curl localhost:8000/api/v1/health` answers and CI is green on the first pull request.
- Before M1, the owner confirms the 12 catalog topics. Before M2, `.env` needs Ollama Cloud, OpenRouter and Langfuse Cloud keys. Before M4: VPS access, DNS records and a GitHub repository, created only when the owner asks.
- ADR 0001 records the proof-of-concept scope.

## Episodic Memory

- [2026-10-12] #event **The project was planned and approved.** The brief asked for a production-grade multi-agent RAG application. A first plan of 12 milestones was replaced the same day by a proof-of-concept scope (ADR 0001): 7 milestones, no accounts, local embeddings, approval by CLI or a minimal page. Later the same day: OpenRouter's free models replaced Groq as the fallback, and memory was split into a public and a private file.

## Semantic Memory

### Product and plan

- #decision **Proof of concept first** (owner, 2026-10-12, ADR 0001). Kept: the LangGraph editorial graphs, hybrid RAG with Ask the notes, a free-provider LLM router, local embeddings, a 30-question eval in CI, Langfuse Cloud, FastAPI with Astro, Compose deploy through GitHub Actions, the How it works page. Deferred: custom topics, accounts and preference memory, a full admin UI, the MCP server.
- #decision **Seven milestones, M0 to M6; production at M4,** right after the editorial graph works, so approved notes accumulate while Ask and the web app are built.
- #decision **Scout is a graph node that runs code:** collect, cluster, rank. A model is called only for borderline clusters. Reason: hundreds of documents per topic a day must be handled repeatably, testably and without spending free quota.
- #decision **Three graphs:** the Topic Planner (per topic, with approval), the edition graph (Scout, per topic per day) and one story graph per picked story (Researcher, Writer, Fact-checker loop of at most 2 rewrites, approval, publish). Each story graph is its own thread with the Postgres checkpointer, so a draft can wait for approval without holding up the run.
- #decision **Approval is approve or reject** in phase 1; "request a rewrite" went with the full review UI.
- #decision **English notes; the catalog uses English-language sources,** to match the English embedding model.
- #decision **Default catalog (12 topics, to be confirmed by the owner):** Formula 1, Premier League, Tennis, Climate tech, Astronomy and spaceflight, Open-weight AI models, Cybersecurity, Electric vehicles, Central banks and markets, Health research, Video games, Film and TV.
- #decision **Defaults:** 15 drafts a day at most (2 per topic); Ask 10 questions per IP a day and 100 in total; daily run at 01:30 UTC; `pg_dump` at 00:30 UTC, 7 copies kept.
- #decision **The CLI is `dan`** (the initials of Daily AI Notes); the owner kept the name on 2026-10-12.
- #decision **The eval set:** 30 questions over a frozen corpus of about 40 notes, 8 unanswerable on purpose. Pull requests check without a model (expected note in the top 5, citations resolve, "not enough" for the unanswerable); a nightly judge on Ollama, from a different family than the Writer, scores faithfulness into `eval_runs`.

### Stack and environment

- #fact **Python 3.14.8** (2026-09-30) is current; image `python:3.14.8-slim-trixie` for amd64 and arm64. **Python 3.15.0** came out 2026-10-09; pyyaml 6.0.3, zstandard 0.25.0, ormsgpack 1.12.2 and uuid-utils publish no 3.15 wheels, and orjson's 3.15 Linux wheels need glibc 2.39 or newer (PyPI, 2026-10-12). CI runs 3.14 only (ADR 0001).
- #fact **Every planned Python package resolves to binary wheels** for 3.14 on x86_64 and aarch64 `manylinux_2_28` and on macOS arm64 (`uv pip compile --only-binary :all:`, 2026-10-12).
- #fact **Latest versions on 2026-10-12** (PyPI): fastapi 0.143.0 (10-08), pydantic 2.14.1 (10-11), pydantic-settings 2.15.0, uvicorn 0.54.0, sqlalchemy 2.1.4 (10-07), alembic 1.20.0, psycopg 3.3.6, procrastinate 3.10.0 (09-23), langchain 1.4.4, langchain-core 1.6.10, langgraph 1.2.14, langgraph-checkpoint-postgres 3.1.2, langfuse 4.17.0, ruff 0.17.0, mypy 2.4.0, pytest 9.1.1, uv 0.13.0 (10-09). Many are under two weeks old, so the release-age floor picks earlier releases at lock time.
- #fact **SQLAlchemy 2.1.0 went final on 2026-09-24;** the latest 2.0 is 2.0.54. SQLAlchemy 2.1 maps a bare `postgresql://` URL to psycopg 3 and needs the `[asyncio]` extra for greenlet.
- #decision **psycopg 3 is the only Postgres driver,** because LangGraph's `AsyncPostgresSaver` requires it. Its connections need `autocommit=True`, `prepare_threshold=0` and `row_factory=dict_row`; `setup()` runs `CREATE INDEX CONCURRENTLY`.
- #decision **Procrastinate is the queue and scheduler:** Postgres-backed with no broker, cron tasks, locks, queueing locks, retries; its CI covers Python 3.14 with PG 18. Rejected: Celery, Dramatiq and Taskiq (need a broker), arq (maintenance only), APScheduler 4 (alpha), PgQueuer (weekly releases, one main maintainer), Temporal and Hatchet (a server each).
- #fact **LangChain has no 2.x.** `create_agent` with middleware replaces `create_react_agent`; `LLMChain` and `AgentExecutor` moved to langchain-classic. Resuming an `interrupt()` with `Command(resume=...)` re-runs the node from its start. Migration guides: docs.langchain.com/oss/python/migrate/langchain-v1 and /langgraph-v1 (2026-10-12).
- #fact **PostgreSQL 18.6** (2026-08-13; 18.5 was never released); PG 19 is in beta. **pgvector 0.8.7** (2026-10-01), image `pgvector/pgvector:0.8.7-pg18-trixie` for amd64 and arm64. The PG 18 image keeps data in `/var/lib/postgresql/18/docker`, so the volume mounts at `/var/lib/postgresql` (docker-library docs, 2026-10-12).
- #fact **Caddy 2.11.7** (2026-10-03); 2.11.6 cut streamed responses after 60 s.
- #fact **Docker Engine 29.9.0, Compose v5.6.0.** Published ports bypass UFW; the default `json-file` log driver never rotates, the `local` driver does (Docker docs, 2026-10-12).
- #fact **Frontend on 2026-10-12** (npm): astro 7.3.8 (needs Node 22.12+), @astrojs/node 11.1.7, @astrojs/react 7.0.1, react 19.3.0, next 16.4.0, pnpm 12.11.2, openapi-typescript 7.13.0, openapi-fetch 0.17.0, vitest 5.0.4. TypeScript 7.0.2 is npm's latest, but @astrojs/check 0.9.10 accepts only 5 or 6, so use 6.0.3. Node 24.21.0 is LTS (maintenance from 2026-10-20); Node 26 becomes LTS on 2026-10-28.
- #insight **Astro 7's Node adapter** stores sessions on the filesystem by default (turn them off), checks the `Host` header against `security.allowedDomains` since 7.3.6 (set it), and needs a fixed `ASTRO_KEY` so server islands survive a deploy.
- #fact **GitHub Actions on 2026-10-12:** checkout v7.0.1, setup-node v7.1.0, cache v6.1.0, astral-sh/setup-uv v10.3.0 (no `@vN` tags since v8), docker/login-action v4.6.0, docker/metadata-action v6.2.0, docker/build-push-action v7.4.0. GHCR is free for public repositories, and new packages start private.
- #fact **pre-commit revs on 2026-10-12:** pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.0, gitleaks v8.30.1. Run mypy as a local hook (`uv run --frozen mypy`).
- #fact **The release-age floor is enforceable:** uv's `exclude-newer` accepts friendly durations ("1 week", "30 days") and ISO 8601 (`P7D`), with per-package overrides in `exclude-newer-package`; pnpm's `minimumReleaseAge` counts minutes (since 10.16; default 1440 since v11) (uv and pnpm docs, 2026-10-12).

### Models and providers

- #decision **Router chain: Ollama Cloud first, then OpenRouter's free models,** with no credit purchase (owner, 2026-10-12). Groq was considered and rejected as the fallback.
- #fact **Ollama Cloud** (ollama.com, 2026-10-12): the free plan has unpublished "starter usage credits" and starter models, 1 concurrent request, and resets monthly from the sign-up date. Credits can be bought on any plan. Pricing per 1M tokens: `gpt-oss:120b` $0.15 in / $0.60 out, `gpt-oss:20b` $0.07 / $0.30. "Prompt or response data is never logged or trained on." The docs say "Ollama's cloud currently does not support structured outputs", and no embedding models are listed.
- #fact **langchain-ollama 1.1.0 should reach Ollama Cloud** with `base_url="https://ollama.com"` and `OLLAMA_API_KEY` set (code inspection, not yet run).
- #fact **OpenRouter free models** (2026-10-12): 20 requests a minute; 50 a day until $10 of credits has ever been bought, then 1,000. 15 `:free` models were listed, and the list changes often. Data policy depends on the model (some train on prompts and keep them); an account setting excludes those providers. `init_chat_model("openrouter:...")` works through langchain-openrouter 0.2.9. No embeddings.
- #fact **Groq's free plan,** per model: 30 requests a minute, 1,000 a day, 8K tokens a minute, 200K a day; no training on inputs (console.groq.com, 2026-10-12).
- #fact **Gemini's free tier** publishes no limits outside AI Studio, uses free-tier data to improve Google's products, and may not serve users in the EEA, Switzerland or the UK (ai.google.dev terms, 2026-10-12).
- #fact **`init_embeddings` prefixes:** azure_ai, azure_openai, bedrock, cohere, google_genai, google_vertexai, huggingface, mistralai, ollama, openai. **`with_structured_output` defaults differ:** Anthropic and Mistral use function calling; OpenAI, Ollama and Google use JSON schema.
- #decision **Local embeddings:** fastembed with `BAAI/bge-small-en-v1.5` (67 MB, 384 dimensions), behind a short LangChain `Embeddings` adapter, because LangChain's own fastembed class lives only in langchain-community. Rejected: sentence-transformers (pulls in PyTorch), an Ollama embedding container.
- #fact **fastembed on Python 3.14:** fastembed 0.9.0 (2026-10-07) and onnxruntime 1.31.0 (2026-10-09) are newest; with a two-week floor, fastembed 0.8.1 with onnxruntime 1.30.0 resolves to wheels on manylinux x86_64 and macOS 14+ arm64. The macOS resolve needs `MACOSX_DEPLOYMENT_TARGET=14.0` (uv pip compile, 2026-10-12).
- #fact **fastembed's small multilingual option** is `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, 0.22 GB); `multilingual-e5-small` is not supported (fastembed supported-models page, 2026-10-12).
- #decision **Langfuse Cloud, Hobby plan:** 50k units a month, 30 days of history, 2 users, hard cap. Self-hosting is sized at 4 cores and 16 GiB with ClickHouse, Redis and S3. SDK v4 uses `propagate_attributes()`; `LANGFUSE_BASE_URL` replaces `LANGFUSE_HOST` (langfuse.com, 2026-10-12).

### Data sources and publisher policy

- #decision **Phase 1 sources:** RSS/Atom with autodiscovery, the arXiv API, GitHub releases through the REST API, Hacker News (Firebase and Algolia). Exa's free monthly credit, when a key is set, helps the Topic Planner discover sources; its results are used for URLs only.
- #fact **Reddit:** new public API requests end 2026-10-31, removals start 2027-01-12, public access closes in March 2027; robots.txt disallows everything (r/redditdev post of 2026-09-30, checked 2026-10-12).
- #fact **GDELT's DOC API** failed 3 probes on 2026-10-12 (429, an empty `{}`, 429); GDELT points users to its Web NGrams files instead.
- #fact **YouTube's API policy** forbids "new or derived data" from API data, so no AI summaries of it (developer policies of 2026-09-14).
- #fact **Limits:** arXiv allows 1 request every 3 s on one connection, and its metadata including abstracts is CC0. GitHub allows 60 requests an hour without a token and 5,000 with one; its robots.txt disallows `/*.atom$`. HN Algolia allows 10,000 requests an hour per IP (2026-10-12).
- #fact **Excluded by their terms:** the Guardian Open Platform (§3(g) bans AI and ML use), NYT (bans grounding and RAG), Google News RSS (personal, non-commercial use only), NewsAPI.org's free plan (development only). Google Custom Search is closed to new customers; Bing Search was retired on 2025-08-11 (2026-10-12).
- #fact **Opt-out signals to honour:** robots.txt per RFC 9309 (5xx means disallow all, 4xx means allow, cache 24 h at most); IETF aipref vocab-08, a draft, with `ai-use`; Cloudflare Content Signals `ai-input=no`, plus a new `use=` field whose managed default is `use=reference` (treat `reference` and `immediate` as link-only); TDMRep; `noai`; `nosnippet`; schema.org `isAccessibleForFree: false` (2026-10-12).

### Design

- #decision **DESIGN.md comes from the v2 page of the owner's Claude Design canvas** (2026-10-12). Admin, How it works, Archive and Topic are v1 screens marked "to revise", used as layout reference only.
- #decision **The note screen says "Approved by the editor"** instead of "Published automatically", because every note is approved.
- #insight **The design's account features wait for phase 2:** feedback buttons, custom topics, delivery time and settings.
- #fact **DESIGN.md lint** (@google/design.md 0.4.0, 2026-10-12): 0 errors, 39 `orphaned-tokens` warnings, all expected: 26 `dark-` tokens, `t1` to `t8`, and `line`, `line-2`, `ink-2`, `ink-3`, `grid`, which CSS applies outside component definitions. The spec requires a `primary` color, so `primary` aliases `accent`; component `padding` takes a single dimension.

### Infrastructure

- #decision **One Compose stack on one VPS behind Caddy;** images in GHCR; `deploy.sh <sha>` over SSH (pull, migrate, `up -d --wait`, health check, redeploy the previous SHA on failure); nightly `pg_dump` with 7 copies; a README setup section instead of a provisioning script (ADR 0001).
- #decision **Starting memory limits:** caddy 64 MB, web 256 MB, api 640 MB, worker 1 GB, db 1.25 GB with `shared_buffers` 512 MB; to be measured with `docker stats` at M4.

### Meta-lessons

- #insight **A decision touches more than one place.** After a reversal, search every file and the plan page for the old answer. On 2026-10-12 "Groq" survived in a table cell and in an unused drawing after the switch to OpenRouter.
- #insight **Research subagents here cannot write report files;** they return findings as text, so save them yourself.

### Preferences

- The owner's preferences live in `.private/MEMORY.md`.

## Procedural Memory

- Filled as the project gains commands; M0 creates `make up` and `make check`.
