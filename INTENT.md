# INTENT.md

Standing instructions for everyone working in this repository, human or AI agent. Read this file
before starting any task. When a rule here changes, update this file in the same commit as the
change, and say why.

Rules live here. What we have learned (the current state, what happened, facts, lessons,
procedures) lives in `MEMORY.md`. Design rationale lives in `docs/design.md` (planned, M6) and in
`docs/adr/`. Commands and paths marked (Mn) are created by that milestone.

## Project

Daily AI Notes (dailyainotes.com) is an open-source, multi-agent RAG application: "AI takes notes
on what's happening, every day, on the things you care about." Every day, LangGraph agents collect
coverage for each catalog topic, cluster duplicate reports into stories, research them, write
short notes with inline citations, fact-check every claim and wait for a human approval before
publishing. Visitors read the notes for the topics they pick and ask questions answered only from
the notes, with citations. It is a portfolio project: architecture, code quality, tests and
documentation count as much as features.

Phase 1 is a proof of concept (ADR 0001): a working, demoable end-to-end pipeline, not
production completeness.

| Phase | Scope | Status |
|---|---|---|
| 1 | Proof of concept: M0 to M6 below | In progress |
| 2 | The README's Next steps: custom topics, accounts and preference memory, full admin UI, MCP server, offsite backups and monitoring | Not started |

Phase 1 is done when, on dailyainotes.com: a visitor picks topics from the 12-topic catalog and
reads today's approved notes for them, each with inline citations and a "how this note was made"
trail; the daily run drafts notes that the owner approves or rejects with `dan review` (M2) or the
minimal /admin page; Ask the notes answers with citations or says the notes don't cover the
question; topic timelines and the How it works page (pipeline, live stats, eval scores, cost per
day) work; CI runs the gate and the 30-question eval on Python 3.14; a merge to `main` deploys,
and a nightly `pg_dump` runs.

## Working Agreement

These apply to every change: code, docs and configuration.

- **Plan before building.** Beyond a small fix, propose the plan with a check per step and wait
  for the owner's approval in words. A decision with real trade-offs is the owner's: ask.
- **Ask when something is ambiguous; don't guess.** Give the recommended option first, with its
  reason. When two readings of a request lead to different work, show both.
- **Stay inside the proof-of-concept scope.** Don't build what ADR 0001 defers; add ideas to the
  README's Next steps instead.
- **Small, reviewable steps.** Each step ends with `make check` (M0) passing and one commit, on a
  working branch, never directly on `main`.
- **Never push, tag, open a pull request or create a remote without being asked.** Before the
  first public push, check the whole history for secrets and private content.
- **Report honestly,** with the output. A skipped or failed check is reported as skipped or
  failed.
- **Simple and explicit over clever.** No unused dependencies; add a package in the step that
  first uses it.
- **When a decision reverses, update every file that carried the old answer** in the same commit,
  and search for the old answer to be sure.
- **Plain prose.** Docs, comments and messages use plain words and short sentences.

## Project Memory

Agent memory of the development process has two files. AGENTS.md sends every agent to both;
Claude Code loads `MEMORY.md` through AGENTS.md and the private file through `CLAUDE.local.md`.

- **`MEMORY.md` is public.** Verified facts with their sources, technical decisions with their
  reasons, lessons, procedures and the current state.
- **`.private/MEMORY.md` is private and gitignored.** The kickoff conversation and the owner's
  answers, the owner's preferences and working style, budget, accounts and server details, and
  personal context. This is the owner's decision (2026-10-12).
- **Never copy private content into committed files,** commit messages, pull requests, issues,
  logs or anything published. A rule that follows from a private reason goes here without the
  reason.
- **End every session by updating them:** Working Memory back to the lines that describe now,
  dated Episodic entries for what happened, durable knowledge promoted into Semantic or
  Procedural. Each item goes in the public or the private file by the split above.
- **Save what is not obvious from the code or git:** a fact you verified (with its source), a
  lesson when a problem cost real time, a decision when the owner decides something.
- **Keep them true.** Correct or delete an entry that turned out wrong. Rules belong in this file.
- **Never write secrets into either file.** Secrets live only in `.env`.

## Coding Standards

- **Python 3.14 with uv.** One package, `dailyainotes`, in `src/`; the CLI is `dan` (M0).
- **Format and lint with ruff, type-check with mypy `--strict` on `src/`.** Both run in
  `make check` and pre-commit (M0).
- **Typed boundaries.** Pydantic models for settings, API bodies, connector configs and every
  structured model output; SQLAlchemy 2 typed mappings (`Mapped[...]`) for tables.
- **Async for I/O.** Database, HTTP and model calls are async. Pure logic in `domain/` stays
  plain functions, so it is trivial to test.
- **Time is UTC.** Timezone-aware datetimes everywhere, `timestamptz` in Postgres; convert only
  for display.
- **One settings module.** All configuration comes from `src/dailyainotes/settings.py` (M0,
  pydantic-settings); every setting appears in `.env.example` (M0) with a comment. Nothing else
  reads the environment.
- **Structured logging.** structlog JSON lines; event names are snake_case past-tense facts
  (`source_fetched`, `claim_checked`). Never log secrets, full article text or raw IP addresses.
- **Comments explain why,** not what.
- **LangChain and LangGraph 1.x APIs only.** No `LLMChain`, `AgentExecutor`,
  `create_react_agent` or langchain-community. Always pass `method=` to
  `with_structured_output`; providers default differently.
- **Domain vocabulary.** topic, topic profile, source, publisher, document, chunk, story,
  edition (one topic, one day), note, note version, citation, claim, claim check, approval, run.
  Use these words in code, tables and docs.
- **Frontend.** TypeScript 6 in strict mode. Components in `web/src/components/ui/` (M6) take
  props only and never fetch; pages and islands do the fetching.
- **Every UI follows DESIGN.md:** the site, the /admin page and diagrams in docs.
- **A change to the visual system updates DESIGN.md's tokens and prose in the same commit.**
  `npx --yes @google/design.md@latest lint DESIGN.md` stays at 0 errors; the only expected
  warnings are `orphaned-tokens` for tokens applied through CSS (the `dark-` tokens, `t1` to `t8`,
  `line`, `line-2`, `ink-2`, `ink-3`, `grid`).

## Architectural Constraints

- **Layers, imports pointing down only:** interfaces (`api`, `worker`, `cli`) → graphs and
  services → adapters (`db`, `sources`, `llm`, `retrieval`) → `domain`. Interfaces never import
  each other. A test in `tests/architecture/` (M0) enforces it.
- **Vendor seams.** Only `llm/` imports model and embedding packages; only `db/` contains SQL;
  every web page fetch goes through the policy-gated fetcher in `sources/`.
- **One datastore: Postgres 18 + pgvector.** It holds data, vectors, the Procrastinate queue and
  the LangGraph checkpoints. No Redis, vector database or other stateful service without a design
  discussion first.
- **Schema changes through hand-written Alembic migrations only,** checked by a drift test (M0).
  A release's migrations only add; removals ship in a later release, so the old image keeps
  working during a deploy.
- **Re-runs are safe.** One edition per topic per day (unique); ingestion upserts by canonical URL
  hash; a graph resumes from its checkpoint instead of starting over.
- **Grounded output only.** Every sentence of a note cites evidence. Ask answers only from
  published notes and says "not enough" instead of guessing. Citations are validated in code.
- **Fact-check rules.** A factual claim needs 2 independent origins, at least one with trust 0.7
  or more, or the primary source for a claim about itself; otherwise it is attributed or cut.
  Independent means a different owner group and not a syndicated copy. The fact-checker uses a
  different model family than the Writer.
- **Nothing publishes without approval.** Every note and every topic profile passes a LangGraph
  interrupt that the owner resolves (owner's decision, 2026-10-12).
- **Copyright.** Show only our own summaries, quotes of at most 25 words per source, and links to
  originals. Never republish full text. Paywalled or AI-opted-out pages are link-only. Source text
  is purged after 30 days. Reddit, Guardian and NYT content is excluded.
- **No accounts in phase 1.** A visitor's topic choice stays in the browser. The only per-visitor
  server state is a hashed-IP rate-limit counter and the Ask log, kept 30 days.
- **Admin is one token** (`ADMIN_TOKEN`), sent as a bearer header and compared in constant time.
- **The LLM router is the only way to call a model.** Each role has an ordered chain of
  `provider:model` in settings; it falls back on rate limits, exhausted quotas, timeouts and
  invalid output. OpenRouter is used only with free models whose providers don't train on
  prompts.
- **Embeddings are local:** fastembed with `BAAI/bge-small-en-v1.5` (384 dimensions). The model
  id is stored with the vectors; changing the model means re-embedding.
- **Neutral coverage.** When sources disagree, the note attributes each position.

## Testing Requirements

- **The gate before every commit is `make check`** (M0): ruff format check, ruff, mypy, pytest,
  and the web checks (`pnpm check`, M6). Integration tests need Postgres up (`make up`, M0).
- **Unit tests never touch the network.** A conftest guard fails any socket connection.
- **Integration tests use a real Postgres test database** and no outside network. Connectors are
  tested against recorded responses in `tests/fixtures/<source>/` (M1) with respx.
- **No live model calls in tests.** Graphs are tested with LangChain's fake chat models. Only the
  nightly eval calls a model.
- **Tests are named after behaviour,** and every bug fix starts with a failing test.
- **Be exhaustive where correctness is the product:** citation checks, independence counting,
  the policy gate, rate limits and the router's fallback.
- **Evals.** The 30-question set in `evals/` (M5) runs on every pull request without a model and
  gates against `evals/baseline.json`. Changing the baseline needs a commit message that says
  why.
- **A skipped test is not a pass.** Read the summary line.

## Dependency Policies

- **Latest stable versions, checked live,** pinned exactly in committed lockfiles (`uv.lock`,
  `pnpm-lock.yaml`).
- **Two-week release-age floor, enforced by the tools:** uv `exclude-newer` and pnpm
  `minimumReleaseAge` (M0). Record every exception and its reason in MEMORY.md.
- **Before adding a package,** check that it is maintained, has wheels for Python 3.14 on Linux
  x86_64 and macOS arm64, and has a license compatible with Apache-2.0 (no GPL or AGPL).
- **Avoid:** langchain-community, PyTorch and sentence-transformers, Redis-backed queues, a second
  Postgres driver (psycopg 3 serves the ORM, the queue and the checkpointer).
- **Pin infrastructure:** Docker images by exact tag, GitHub Actions by commit SHA, pre-commit
  hooks by rev.
- **Why not newer yet** (checked 2026-10-12):
  - TypeScript 7: `@astrojs/check` accepts only 5 or 6.
  - Node 26: becomes LTS on 2026-10-28; use Node 24 LTS until then.
  - Python 3.15: pyyaml, zstandard, ormsgpack and uuid-utils publish no 3.15 wheels.
  - PostgreSQL 19: still in beta.
- **SQLAlchemy 2.1** (final since 2026-09-24) is accepted; fall back to 2.0.x if M0's tests fail.
- **Free tiers first.** Any paid service needs the owner's approval and a quoted monthly cost
  first.

## Security

- **Secrets are never committed.** `.env` is ignored; `.env.example` lists every key with an
  empty value; gitleaks runs in pre-commit and CI (M0).
- **`.private/` and `CLAUDE.local.md` are gitignored.** Their content never leaves them.
- **Everything fetched or typed by visitors is untrusted data:** pages, feeds, model output,
  questions. It is passed to models as quoted data, never as instructions; model output is
  schema-validated; no tool inside a graph has side effects.
- **Be a polite client.** User-Agent `DailyAINotes/<version> (+https://dailyainotes.com)`;
  robots.txt per RFC 9309; per-host rate limits; back off on 429 and 5xx and honour
  `Retry-After`.
- **Network exposure.** Only Caddy publishes ports (80 and 443), since Docker-published ports
  bypass UFW. Postgres is never exposed. Admin endpoints require the token. Ask is rate-limited
  per hashed IP and globally.

## Performance and Cost

- **Free quotas are the budget.** A daily draft cap (default 15, at most 2 per topic); a per-provider
  daily token budget in the router; one request at a time to Ollama; OpenRouter's free requests
  go to the pipeline before Ask.
- **Ask limits:** 10 questions per IP a day and 100 a day in total. No model call when retrieval
  finds nothing strong.
- **Work only when something changed.** Conditional requests (ETag, Last-Modified) for feeds;
  each document embedded once; no new note for a story already covered unless new reports arrive.
- **Every container has a memory limit;** the embedding model loads once per process.
- **Cost is tracked per run, topic and day** in the `llm_calls` table (M2), the source of truth
  for the How it works page.

## Standing Tasks

### High: phase 1 (proof of concept)

- [ ] M0 Foundations: uv project, settings, logging, Compose with Postgres, Alembic baseline and drift test, `/api/v1/health`, `dan`, pre-commit, CI on 3.14, license, README stub → check: `make up && make check`; `curl localhost:8000/api/v1/health`; CI green on the first pull request
- [ ] M1 Ingestion and hybrid search: catalog, RSS/Atom, arXiv, GitHub releases, HN, policy-gated fetcher, local embeddings, fused search → check: `dan ingest --topic formula-1`; `dan search "safety car" --explain`; a fixture test per connector and policy signal
- [ ] M2 LLM router and Topic Planner: fallback chains, structured-output probe, budget guard, usage ledger, Langfuse; planner graph with approval → check: `dan llm probe`; `dan topics plan astronomy`, then `dan review approve <id>`; the trace in Langfuse
- [ ] M3 Editorial graph: Scout node, story graph (Researcher, Writer, Fact-checker loop, approval, publish), daily schedule → check: `dan edition run --topic climate-tech`; a planted wrong number loops back to the Writer; `dan review approve <id>` publishes
- [ ] M4 Deploy: Dockerfiles, `compose.prod.yml`, Caddyfile, `deploy.sh`, GHCR and SSH workflow, nightly `backup.sh`, README setup → check: `https://dailyainotes.com/api/v1/health`; the nightly run drafts notes on the VPS; last night's dump restores into a scratch database
- [ ] M5 Ask the notes and evals: search over notes, citation validation, "not enough", per-IP limits, streaming; 30-question eval → check: a cited answer from the Ask endpoint; "Not enough in the notes" for an off-catalog question; the eval gate in CI
- [ ] M6 Web app and How it works: Astro from DESIGN.md, topic picker, daily page, note, timeline, Ask, How it works, minimal /admin; README and docs/design.md → check: on dailyainotes.com, pick topics, read, ask, approve at /admin; `pnpm check` in CI

### Medium

- [ ] Before M1: the owner confirms or edits the 12 catalog topics (the default list is in MEMORY.md).
- [ ] At M2: choose models with `dan llm probe` (Writer and fact-checker from different families) and record them in MEMORY.md.
- [ ] Before M4: confirm the VPS disk size and the DNS records for dailyainotes.com.
- [ ] After 2026-10-28: move to Node 26 LTS.
- [ ] Revise DESIGN.md when the v1 screens (Admin, How it works, Archive, Topic) are redesigned; until then they are layout reference only.
- [ ] Keep the README's Next steps in line with ADR 0001.

### Recurring

- [ ] Monthly: re-check dependencies, free-tier limits (Ollama Cloud, OpenRouter, Langfuse) and Python 3.15 wheels.
- [ ] Monthly: review this file and remove rules nobody follows or needs.
- [ ] At the end of each milestone: consolidate the Episodic tier of both memory files.
