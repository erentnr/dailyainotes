# MEMORY.md: Agent Memory

Persistent memory for AI agents working on Daily AI Notes, modeled on agentmemory's pipeline of observations, compression, and tiered consolidation (github.com/rohitg00/agentmemory). It serves the development process only.

**Convention:** read this file at session start (AGENTS.md sends every agent here; Claude Code loads it through AGENTS.md's import); the Semantic and Procedural tiers are ground truth. This file is public. Its private counterpart, `.private/MEMORY.md`, is gitignored and holds what INTENT.md's Project Memory section lists as private. At session end: append dated observations to Episodic, promote durable knowledge into Semantic/Procedural, and keep Working Memory to the 3–5 lines that describe now. One line per memory, prefixed `[YYYY-MM-DD]`, tagged `#decision` `#insight` `#bug` `#preference` `#fact` `#event`. At each consolidation, every Episodic entry is promoted or deleted; the full pre-consolidation log lives in git. Rules belong in INTENT.md, not here.

Started 2026-10-12; no consolidation yet.

## Working Memory

- **[2026-10-13] M0 to M5's code is merged into `main`; M6 (the web app and How it works) is next.** The work runs on the default catalog, as the owner asked to proceed on every decided default. CI is written but has never run: it needs the GitHub repository, created only when the owner asks. M4's live check needs the repository, VPS access (the `deploy` user), DNS records and the GitHub settings in the README.
- **M2's, M3's and M5's live checks wait for keys in `.env`:** `OLLAMA_API_KEY`, `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`. Then: `dan llm probe`, `dan topics plan --all`, `dan edition run --all`, `dan review list`, `dan ask` on a published note, `dan evals run --judge`, and a trace in Langfuse. Without keys, model calls fail cleanly with `MissingKeyError`. Today's Formula 1 edition (2026-10-12 UTC) has two picked stories waiting in `drafting`; a rerun with keys resumes them.
- ADR 0001 records the proof-of-concept scope.

## Episodic Memory

- [2026-10-12] #event **The project was planned and approved.** The brief asked for a production-grade multi-agent RAG application. A first plan of 12 milestones was replaced the same day by a proof-of-concept scope (ADR 0001): 7 milestones, no accounts, local embeddings, approval by CLI or a minimal page. Later the same day: OpenRouter's free models replaced Groq as the fallback, and memory was split into a public and a private file.

- [2026-10-12] #event **M0 Foundations was built** in five commits: the Python project and gate, Postgres with Alembic and the drift test, the API with `/api/v1/health`, the architecture and no-network guards, pre-commit and CI. Each guard was broken once and its test failed. The gitleaks history scan found no leaks, and the hook blocked a fake token.

- [2026-10-13] #event **M1 Ingestion and hybrid search was built and demoed live.** `dan ingest --topic formula-1` saved 112 documents from 6 feeds in 105 s (90 s of it CPU, mostly local embedding, on the owner's Mac): formula1.com, RaceFans and The Race mostly `full`; Autosport, Motorsport.com and BBC all `link_only`. `dan search "safety car" --explain` returned relevant RaceFans, The Race and formula1.com chunks, with full-text and vector ranks shown.

- [2026-10-13] #event **M3 The editorial graph was built; its model half waits for keys.** `dan edition run --all --no-collect` on the live Formula 1 data made 66 stories in the 36-hour window (60 single reports, 4 of 2, 1 of 3, 1 of 4) and picked the two best a model may read: "Norris concedes he 'let down' McLaren" (4 reports from 3 publishers) and the Antonelli penalty story (3 from 2). The Singapore Grand Prix result ranked third but only link-only publishers covered it, so it was not picked. Both story graphs stopped at the Researcher with `MissingKeyError`, and the edition was marked failed.

- [2026-10-13] #event **M4 Deploy was rehearsed locally.** With a local registry standing in for GHCR and `DOMAIN=localhost`, `deploy.sh` deployed a good tag, rolled a broken one back to it, and the worker ran a deferred `daily_edition` job in its container (Success, 0.29 s). `backup.sh` wrote a dump and `restore-check.sh` restored it into a scratch database. Idle memory: worker 158 MiB, API 82 MiB, Postgres 79 MiB, Caddy 17 MiB (Docker Desktop, arm64). The rehearsal caught two bugs: `deploy.sh` reported success after a failed health check, and the worker built its Procrastinate app in `__main__`.

- [2026-10-13] #event **M5 Ask the notes and the eval set were built.** With the real embedding model, `dan evals run` scored 1.0 on recall at 5, MRR and "not enough" for the 8 uncovered questions; lowering the strong-match threshold to 0.4 dropped "not enough" to 0.0 and the command failed against the baseline. `dan ask` on the development database, which has no published notes, answered "Not enough in the notes to answer that." without a model call.

## Semantic Memory

### Product and plan

- #decision **Proof of concept first** (owner, 2026-10-12, ADR 0001). Kept: the LangGraph editorial graphs, hybrid RAG with Ask the notes, a free-provider LLM router, local embeddings, a 30-question eval in CI, Langfuse Cloud, FastAPI with Astro, Compose deploy through GitHub Actions, the How it works page. Deferred: custom topics, accounts and preference memory, a full admin UI, the MCP server.
- #decision **Seven milestones, M0 to M6; production at M4,** right after the editorial graph works, so approved notes accumulate while Ask and the web app are built.
- #decision **Scout is a graph that runs code:** collect, cluster, rank. Reason: hundreds of documents per topic a day must be handled repeatably, testably and without spending free quota. The planned model check for borderline clusters was cut at M3 (2026-10-13), as the plan's scope-cut list allowed; the calibrated threshold does the job.
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
- #decision **Local and CI Postgres run `pgvector/pgvector:0.8.6-pg18-trixie`** (PostgreSQL 18.6, checked with `select version()`), because 0.8.7 was 11 days old on 2026-10-12. 0.8.7 only fixes IVFFlat index builds and an `avg` edge case; we use HNSW. Move to 0.8.7 after 2026-10-15.
- #decision **Python 3.14.8 is used although it was 12 days old on 2026-10-12:** `.python-version` says `3.14`, uv picks the newest patch, and patch releases carry bug and security fixes. The two-week floor applies to packages.
- #fact **The two-week floor in practice** (M0, 2026-10-12): uv writes `exclude-newer-span = "P2W"` to `uv.lock`, and `uv lock --check` passes with it. It picked pydantic 2.13.5, SQLAlchemy 2.1.1, typer 0.27.2, mypy 2.3.1 and ruff 0.16.9 over newer releases.
- #insight **Starlette 1.7.0 deprecates `httpx` in its TestClient** ("install `httpx2` instead"), so the dev group uses httpx2 2.13.1 and pytest runs with `filterwarnings = ["error"]` to catch such deprecations. Earlier research found that respx cannot mock httpx2.
- #decision **Connectors use httpx2, and tests serve recorded fixtures through `httpx2.MockTransport`; no respx** (M1, 2026-10-12). httpx itself has had no release since 0.28.1 (2024-12-06), and httpx2 (Pydantic's continuation, 2.13.1) has the same API, including `AsyncClient` and `MockTransport` (probed).
- #decision **The catalog is TOML (`config/catalog.toml`, read with the standard library's `tomllib`),** not the plan's `catalog.yaml`, to avoid a YAML dependency (M1, 2026-10-12). `dan catalog sync` adds and updates and never deletes, so sources the Topic Planner adds survive a sync.
- #insight **Services must not import SQLAlchemy** (the vendor-seam test). They type engines with the `AsyncEngine` that `db/engine.py` re-exports.
- #insight **Uvicorn logs its first lines before the app's lifespan runs,** so `create_app` configures logging itself; then every line uvicorn writes is JSON (checked with a live run, 2026-10-12).
- #insight **gitleaks' pre-commit hook scans only staged changes** (`gitleaks git --pre-commit --staged`), so CI scans the whole history with the pinned `zricethezav/gitleaks:v8.30.1` image and skips the hook (2026-10-12).
- #decision **CI pins uv 0.12.20 and astral-sh/setup-uv v10.2.0,** the newest releases at least two weeks old on 2026-10-12. uv 0.12.20 reads the lockfile uv 0.13.0 writes, including `exclude-newer-span` (checked with `uv lock --check` and `uv sync --locked`).
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

- #decision **The router is its own loop over a role's chain, not LangChain's `with_fallbacks`,** because invalid output and spent daily budgets must also move it to the next model (M2, 2026-10-13). Every provider gets the JSON request in the prompt, checked with Pydantic, with one repair attempt; `dan llm probe` reports whether native JSON-schema output also works per model.
- #decision **Every OpenRouter request sends `openrouter_provider={"data_collection": "deny"}`.** OpenRouter documents `deny` as "use only providers which do not collect user data" (docs, 2026-10-13); with no such provider the request fails and the router moves on.
- #decision **No `model_prices` table** (M2, 2026-10-13): on free plans every call costs $0. `llm_calls` records tokens, latency and outcome, and keeps a `cost_usd` column for a paid model the owner might approve later.
- #decision **LangGraph state holds plain JSON** (dicts and lists), so checkpoints never deserialize our classes. The checkpointer lives in the `langgraph` schema, which the drift test does not compare.
- #fact **Versions the floor picked for M2** (2026-10-13): langchain 1.4.3, langchain-core 1.6.5, langgraph 1.2.12, langgraph-checkpoint-postgres 3.1.2, langchain-ollama 1.1.0, langchain-openrouter 0.2.9, langfuse 4.15.6. `init_chat_model` splits `provider:model` at the first colon, so `ollama:gpt-oss:120b` works; `StateGraph.add_sequence` exists.
- #insight **langchain-core warns "Core Pydantic V1 functionality isn't compatible with Python 3.14" at import.** Both pytest (`filterwarnings`) and the package `__init__` ignore exactly that message (2026-10-13).
- #insight **`FakeListChatModel` restarts its replies in every new instance,** which exposed that the router rebuilt the model for its repair attempt; it now builds each model once per provider (2026-10-13).
- #insight **The development database needs `uv run dan db upgrade` after every new migration;** the test database migrates itself on each run (2026-10-13).
- #fact **Ollama Cloud's model list** (`https://ollama.com/api/tags`, 2026-10-13): deepseek-v4-pro, deepseek-v4.1-flash, gemma4:31b, glm-5.2, glm-5.3, glm-5.3-flash, gpt-oss:120b, gpt-oss:20b, kimi-k2.6, kimi-k2.7-code, kimi-k3, minimax-m2.7, minimax-m3, mistral-large-3:675b, mistral-large-4, nemotron-3-nano:30b, nemotron-3-super, nemotron-3-ultra. Which of them the free plan's "starter models" include is not published.
- #fact **OpenRouter's free models** (`/api/v1/models`, 2026-10-13) still number 15, among them google/gemma-4-31b-it, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b and nvidia/nemotron-3-ultra-550b-a55b. The public endpoints API does not show each provider's data policy, so whether a model works with `data_collection: deny` shows only in `dan llm probe` with a key.
- #decision **Default chains per role** (M3, 2026-10-13): Researcher and Writer `ollama:gpt-oss:120b`, then `openrouter:google/gemma-4-31b-it:free`; the claim extractor `ollama:gpt-oss:20b`, then the same Gemma; the verifier `ollama:gemma4:31b`, then `openrouter:nvidia/nemotron-3-super-120b-a12b:free`, another family than the Writer's. To be confirmed with `dan llm probe` once keys exist.

### Data sources and publisher policy

- #decision **Phase 1 sources:** RSS/Atom with autodiscovery, the arXiv API, GitHub releases through the REST API, Hacker News (Firebase and Algolia). Exa's free monthly credit, when a key is set, helps the Topic Planner discover sources; its results are used for URLs only.
- #fact **Reddit:** new public API requests end 2026-10-31, removals start 2027-01-12, public access closes in March 2027; robots.txt disallows everything (r/redditdev post of 2026-09-30, checked 2026-10-12).
- #fact **GDELT's DOC API** failed 3 probes on 2026-10-12 (429, an empty `{}`, 429); GDELT points users to its Web NGrams files instead.
- #fact **YouTube's API policy** forbids "new or derived data" from API data, so no AI summaries of it (developer policies of 2026-09-14).
- #fact **Limits:** arXiv allows 1 request every 3 s on one connection, and its metadata including abstracts is CC0. GitHub allows 60 requests an hour without a token and 5,000 with one; its robots.txt disallows `/*.atom$`. HN Algolia allows 10,000 requests an hour per IP (2026-10-12).
- #fact **Excluded by their terms:** the Guardian Open Platform (§3(g) bans AI and ML use), NYT (bans grounding and RAG), Google News RSS (personal, non-commercial use only), NewsAPI.org's free plan (development only). Google Custom Search is closed to new customers; Bing Search was retired on 2025-08-11 (2026-10-12).
- #fact **Opt-out signals to honour:** robots.txt per RFC 9309 (5xx means disallow all, 4xx means allow, cache 24 h at most); IETF aipref vocab-08, a draft, with `ai-use`; Cloudflare Content Signals `ai-input=no`, plus a new `use=` field whose managed default is `use=reference` (treat `reference` and `immediate` as link-only); TDMRep; `noai`; `nosnippet`; schema.org `isAccessibleForFree: false` (2026-10-12).

- #fact **How the starter sources answer us** (live ingest, 2026-10-13): autosport.com and motorsport.com return 403 to our User-Agent, so their items are link-only. bbc.co.uk's robots.txt blocks ten AI crawlers, so BBC items are link-only. formula1.com marks some pages `isAccessibleForFree: false`. formula1.com's feed items carry no publication date. racefans.net and the-race.com pages extract in full.
- #insight **A test that compares outcomes can miss wasted work.** The first deduplication test passed with deduplication broken, because the unique key still stopped duplicates; it now asserts that a second run requests no article page (M1, 2026-10-13).
- #insight **SQLAlchemy 2.1 types `select(Chunk.id)` as `Select[int]`** (a TypeVarTuple), not 2.0's `Select[tuple[int]]` (mypy, 2026-10-13).
- #fact **fastembed downloads the model from Hugging Face on first use** (64 MB into `EMBEDDING_CACHE_DIR`) and warns about unauthenticated requests; harmless. Unit tests use a word-hash stand-in instead, so no test downloads the model (2026-10-13).

### Editorial graph

- #decision **Clustering threshold 0.92** (cosine to a story's centroid, `domain/clustering.py`), calibrated on the live Formula 1 data with bge-small (M3, 2026-10-13): at 0.88 different events merged; at 0.92 same-event reports stay together, and only the sprint pole and the Grand Prix pole still blur.
- #decision **A story needs at least one document a model may read.** Stories only link-only publishers covered are saved with the reason "only link-only reports" and never picked; their documents never reach a model (M3, 2026-10-13).
- #decision **Code checks before model checks.** `check_citations` finds a sentence without a marker, a marker that points nowhere, a number or a quote missing from the cited evidence; a draft with problems goes back to the Writer without a model check. The extractor and verifier run only on a draft that passes.
- #decision **The independence rule runs after the verifier.** When it downgrades a claim the model called supported, the rationale says why ("Only 1 independent origin supports it…"), for both the Writer's rewrite and the owner's review.
- #decision **The edition runner is a function, not a graph** (`graphs/edition.py`): Scout's thread is `edition:<slug>:<date>`, each story's is `note:<story id>`. A rerun skips a done edition, reuses Scout's picks, and resumes a story graph from its last checkpoint with `ainvoke(None, config)`, under the same run.
- #decision **The daily schedule moved from M3 to M4's worker** (Procrastinate), because M3 has nowhere to run it; `dan edition run --all` does the day's work by hand.
- #fact **Editions are dated by the UTC day,** like the free plans' daily limits.
- #insight **On a Core connection, `select(Model)` returns column rows, not objects,** so `.scalar_one()` gives the id. Select explicit columns into dataclasses instead (M3, 2026-10-13).
- #insight **`string_agg` with an order needs `aggregate_order_by`;** `within_group` renders `string_agg(…) WITHIN GROUP (…)`, which Postgres rejects (M3, 2026-10-13).
- #insight **Integration tests truncate the `langgraph` checkpoint tables too,** because thread ids like `note:1` name rows whose ids restart at 1 in every test.

### Ask and evals

- #decision **Ask is search, then at most one model call.** A note is a strong match when full-text search finds it or its cosine similarity is at least 0.62; with none, Ask answers "Not enough in the notes to answer that." without a model. Calibration on the eval set (2026-10-13, bge-small): expected notes 0.70 to 0.91, the best note for an off-corpus question at most 0.54, unrelated notes next to a good match 0.50 to 0.68.
- #decision **Ask streams server-sent events** (`sources`, `text`, `done` or `error`) from `POST /api/v1/ask`; `AnswerFilter` drops markers that point at no source while streaming and turns a model's `NOT_ENOUGH` into the standard reply. The router falls back only before the first piece of text.
- #decision **Ask's chain is Ollama only** (`LLM_ASK=ollama:gpt-oss:120b`), so OpenRouter's 50 free requests stay with the pipeline; the judge is `ollama:gemma4:31b`.
- #decision **Visitors' IPs are stored only as HMAC-SHA256 hashes** keyed by `IP_HASH_KEY`; without the key the API makes a random one at start, and the day's limits reset when it restarts. Uvicorn trusts `X-Forwarded-For` (`FORWARDED_ALLOW_IPS=*`) because only Caddy can reach the API.
- #decision **The eval corpus is fictional** (40 notes in 8 catalog topics, 30 questions, 4 of them paraphrased): there were no published notes yet, and inventing news about real people or committing publishers' text would both break the rules. The model-free run in CI scores retrieval; the worker's 04:00 UTC run adds the Ask model and the judge (about 44 Ollama calls) and records `ask-judged` in `eval_runs`.
- #insight **The first eval set was too easy:** every question named its note's subject, so every score was 1.0 whatever the threshold between 0.5 and 0.7. Four questions were rewritten as paraphrases; the scores stayed 1.0, but the set now separates the two sides more honestly.
- #insight **pre-commit's mypy hook checks the whole `src` tree, untracked files included,** so a commit of part of a change fails when new untracked files depend on unstaged edits; commit such a step whole.
- #insight **`httpx2.ASGITransport` does not run the app's lifespan;** API tests set `app.state.engine` themselves and override `ask_deps`.
- #insight **`dan review approve` loads the real embedding model** to index the note; tests replace `dailyainotes.cli.LocalEmbeddings`, or CI, without the model cache, would hit the network guard.

### Design

- #decision **DESIGN.md comes from the v2 page of the owner's Claude Design canvas** (2026-10-12). Admin, How it works, Archive and Topic are v1 screens marked "to revise", used as layout reference only.
- #decision **The note screen says "Approved by the editor"** instead of "Published automatically", because every note is approved.
- #insight **The design's account features wait for phase 2:** feedback buttons, custom topics, delivery time and settings.
- #fact **DESIGN.md lint** (@google/design.md 0.4.0, 2026-10-12): 0 errors, 39 `orphaned-tokens` warnings, all expected: 26 `dark-` tokens, `t1` to `t8`, and `line`, `line-2`, `ink-2`, `ink-3`, `grid`, which CSS applies outside component definitions. The spec requires a `primary` color, so `primary` aliases `accent`; component `padding` takes a single dimension.

### Infrastructure

- #decision **One Compose stack on one VPS behind Caddy;** images in GHCR; `deploy.sh <sha>` over SSH (pull, migrate, `up -d --wait`, health check, redeploy the previous SHA on failure); nightly `pg_dump` with 7 copies; a README setup section instead of a provisioning script (ADR 0001).
- #decision **Starting memory limits:** caddy 64 MB, web 256 MB, api 640 MB, worker 1 GB, db 1.25 GB with `shared_buffers` 512 MB; to be measured with `docker stats` at M4.
- #decision **One image for the API, the worker and `dan`** (`Dockerfile`), with the embedding model downloaded at build time into `/app/models`, so the server never fetches it. It runs as uid 10001 and is 933 MB, mostly ONNX Runtime and the LangChain stack (2026-10-13).
- #decision **The production Compose project is `dailyainotes-prod`,** not the development `dailyainotes`, so running it on a development machine cannot take over the development database's container and volume.
- #decision **Procrastinate's tables live in a `procrastinate` schema** (migration 0005 creates the schema, the worker creates the tables on its first start), outside the drift test, like LangGraph's. Upgrading Procrastinate means applying its own SQL migrations by hand.
- #decision **CI deploys only when the repository variable `DEPLOY_HOST` is set;** until then it builds and pushes images. Pull requests build the image without pushing it.
- #insight **bash ignores `set -e` inside a function called from `if`,** so `deploy.sh` once reported "deployed" after a failed health check; its steps are now one `&&` chain (M4 rehearsal, 2026-10-13).
- #insight **`python -m dailyainotes.worker` builds a second Procrastinate app in `__main__`,** which cannot find tasks registered on the module's app (Procrastinate warns "App is instantiated in the main Python module"). The worker starts through the `dan-worker` console script instead.
- #fact **onnxruntime 1.30's Linux build ships Microsoft's telemetry client** (1DS, HTTPS uploads; the library's strings include "telemetry HTTPS uploads"). `ORT_DISABLE_TELEMETRY=1` turns it off; `llm/embeddings.py` sets it before fastembed loads (checked in the image, 2026-10-13).
- #fact **Deploy-side versions on 2026-10-13:** docker/login-action v4.6.0 (2026-07-29), docker/build-push-action v7.4.0 (2026-09-15), docker/setup-buildx-action v4.4.1 (2026-09-16), all pinned by SHA; images `caddy:2.11.7-alpine`, `python:3.14.8-slim-trixie`, `ghcr.io/astral-sh/uv:0.12.20`. actionlint 1.7.12 and shellcheck 0.11.0 lint the workflow and scripts (run in Docker). Docker's Ubuntu install now writes a deb822 `docker.sources` file (docs.docker.com, 2026-10-13).

### Meta-lessons

- #insight **A decision touches more than one place.** After a reversal, search every file and the plan page for the old answer. On 2026-10-12 "Groq" survived in a table cell and in an unused drawing after the switch to OpenRouter.
- #insight **Research subagents here cannot write report files;** they return findings as text, so save them yourself.

### Preferences

- The owner's preferences live in `.private/MEMORY.md`.

## Procedural Memory

- **First setup:** `uv sync`, `cp .env.example .env`, `uv run pre-commit install`.
- **Postgres:** `make up` starts it in Docker and waits until it is healthy; `make down` stops it.
- **The gate:** `make check` runs ruff format (check), ruff, mypy and pytest. Integration tests need `make up`; without it they error rather than skip.
- **The API:** `make api`, then `curl localhost:8000/api/v1/health`.
- **Migrations:** `uv run dan db upgrade` applies them. For a schema change, add the models in `src/dailyainotes/db/tables.py`, write `src/dailyainotes/db/migrations/versions/NNNN_<slug>.py` by hand with revision `"NNNN"`, and keep the drift test green.
- **Catalog and ingestion:** `uv run dan catalog sync` loads `config/catalog.toml`; `uv run dan ingest [--topic <slug>]` fetches the active topics' sources (the first run downloads the embedding model); `uv run dan search "<query>" --explain [--topic <slug>]`.
- **Models and planning:** `uv run dan llm probe` tries every model in the configured chains. `uv run dan topics plan <slug>` (or `--all` for every draft topic) runs the Topic Planner until it waits; `uv run dan review list`, `show plan-<id>`, `approve plan-<id>` or `reject plan-<id> --comment "<why>"`.
- **Editions and notes:** `uv run dan edition run <slug>` (or `--all`; `--no-collect` skips fetching) runs Scout and a story graph per picked story until each note waits; `uv run dan review show note-<id>` prints the note, its sources and each claim's verdict; `approve note-<id>` publishes it, `reject note-<id> --comment "<why>"` rejects it.
- **Packages:** `uv add <package>` or `uv add --dev <package>`; the two-week floor applies automatically. On macOS, packages with ONNX Runtime need `MACOSX_DEPLOYMENT_TARGET=14.0 uv add ...` to resolve.
- **Ask and evals:** `uv run dan ask "<question>" [--topic <slug>]`; `uv run dan evals run` (add `--judge` for the model and judge, `--record` to save into `eval_runs`, `--update-baseline` to rewrite `evals/baseline.json`, and say why in the commit).
- **The worker:** `uv run dan-worker` runs the queue locally; on the server it is the `worker` service.
- **Deploy:** README, Deploy. On the server, in `/srv/dailyainotes`: `./deploy.sh <sha>` deploys or rolls back; `TAG=$(cat .deployed) docker compose -f compose.prod.yml exec worker dan <command>` runs `dan`; `./backup.sh` and `./restore-check.sh`.
- **Rehearse a deploy locally:** copy `deploy/` to a scratch folder with a dummy `.env` (`IMAGE=localhost:5000/dailyainotes`, `DOMAIN=localhost`, a throwaway `POSTGRES_PASSWORD`); run `registry:3` on `127.0.0.1:5000`; push the image there; after the first run, copy Caddy's root certificate out (`docker compose -f compose.prod.yml cp caddy:/data/caddy/pki/authorities/local/root.crt .`) and set `CURL_CA_BUNDLE` to it; afterwards `docker compose -f compose.prod.yml down -v`.
- **Lint the workflow and scripts:** `docker run --rm -v "$PWD:/repo:ro" --workdir /repo rhysd/actionlint:1.7.12` and `docker run --rm -v "$PWD/deploy:/mnt:ro" koalaman/shellcheck:v0.11.0 /mnt/*.sh`.
- **Secrets scan of the history:** `docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:v8.30.1 git /repo --redact --verbose`.
