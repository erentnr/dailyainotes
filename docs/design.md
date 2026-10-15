# Design and trade-offs

The decisions that shape Daily AI Notes, and what each one gave up. The evidence behind them (versions, limits, measurements, dates) is in [MEMORY.md](../MEMORY.md); the scope is in [ADR 0001](adr/0001-proof-of-concept-scope.md).

## One edition per topic, then fan-out

Research and writing run once per topic per day; every reader of a topic gets the same notes, and a reader's page is just the notes on their topics. Cost grows with the number of topics, not the number of readers. In phase 1 the fan-out is trivial: there are no accounts, the reader's topics live in the browser, and the daily page asks the API for the latest day's notes on them.

The day's budget is fixed in code: at most 2 stories per topic and 15 a day, because the free model plans are the budget.

## Three graphs, one runner

| Graph | Runs | Nodes | Waits for |
| --- | --- | --- | --- |
| Topic Planner | per topic, once | draft a profile (model) → discover and validate feeds (code) → propose | the owner, then activates the topic |
| Scout | per topic, nightly | collect → cluster → rank, all code | nothing |
| Story | per picked story | research → write → citation check → extract claims → verify → gate | the owner, then publishes |

The nightly runner (`graphs/edition.py`) is a plain function: a fixed sequence is not an agent. Each story graph is its own thread in the Postgres checkpointer, so a note can wait for approval for days, and a run that fails part-way resumes from its last checkpoint instead of starting over. Approving resumes the same thread from `dan review` or `/admin`.

Models are called only where judging text matters: the Topic Planner's profile, the Researcher, the Writer, claim extraction, verification, and the Ask answer. The rest is code because code is repeatable, testable and free.

## Clustering

Each document's first chunk (title and lead) is embedded locally with `BAAI/bge-small-en-v1.5`. Scout clusters a topic's last 36 hours in one pass, in publication order: a document joins the story whose centroid is most similar, if the cosine similarity is at least 0.92, and starts a new story otherwise.

The threshold was calibrated on a live Formula 1 race weekend: at 0.88 different events merged, at 0.92 reports of one event stayed together. Splitting an event in two is the safer error: a duplicate costs the editor one rejection, while a note that merges two events misleads. A model check for borderline clusters was planned and cut; the calibrated threshold does the job.

Stories are ranked by independent coverage: the best trust score in each owner group, summed, plus small terms for size and freshness. Many copies from one group count once.

## Copyright and source trust

Every page passes a policy gate before its text is kept: robots.txt (RFC 9309), Content-Signal and aipref headers, blocks on known AI crawlers, X-Robots-Tag, TDMRep, meta robots and paywall markup. The result is `full`, `summary` (title and lead only) or `link_only`. Link-only documents are used for search and clustering and never reach a model; a story only link-only publishers covered is never picked. Source text is purged after 30 days.

Notes are our own summaries. Quotes are at most 25 words, and every note links to its sources. Publishers get a trust prior by kind (primary 0.85, wire 0.80, editorial 0.75, specialist 0.60, unknown 0.50, user-generated 0.35), and an owner group, so syndicated copies are not counted as independent.

## Fact-checking

Checks that can be counted are code. `check_citations` rejects a sentence without a marker, a marker that points nowhere, a number that is not in the cited source, and a quote that is not verbatim. A failing draft goes back to the Writer with the problems listed, without spending a model call on verification.

A passing draft is split into claims, and a model from another family than the Writer's judges each claim against only the sources it cites. Code then applies the independence rule: a factual or numeric claim needs two independent origins, one with trust 0.7 or more, or a primary source; an attributed claim ("the team says") needs only its source. A downgraded claim's rationale says why, for the Writer's next attempt and for the editor. Rewrites stop at two; a note that is still weak reaches the editor with its weak claims marked.

## Retrieval

Hybrid search runs in Postgres: a generated `tsvector` with a GIN index for full text, and pgvector's HNSW index for cosine similarity, merged by reciprocal rank fusion (k = 60). Fusion needs no calibration between the two scores. The reranker is an interface with a default that keeps fusion's order, so one can be added without touching callers.

## Ask the notes

Ask searches published notes only. A note is a strong match when full-text search finds it or its similarity is at least 0.62. On the eval set the expected notes scored 0.70 to 0.91 and the best note for an off-corpus question at most 0.54. With no strong match, Ask answers "Not enough in the notes to answer that." without calling a model. Otherwise one model answers from at most 5 notes, streamed as server-sent events. Code drops any citation marker that points at no source while it streams, and a model's own "not enough" becomes the standard reply.

Ask is limited to 10 questions per IP and 100 in total a day. IP addresses are stored only as keyed hashes, and the log is purged after 30 days.

## The model router

Each role has an ordered chain of `provider:model` in settings: Ollama Cloud first, then OpenRouter's free models, which are asked never to use providers that collect prompts. The router is its own loop rather than LangChain's `with_fallbacks`, because invalid output and a spent daily budget must also move it on. Structured output is requested in the prompt and validated with Pydantic, with one repair attempt, which works on every provider. Every call is recorded in `llm_calls` with its tokens and latency; that table is the source for cost per run, topic and day. Ask uses Ollama only, so OpenRouter's 50 free requests a day go to the pipeline.

## Data model

| Area | Tables |
| --- | --- |
| Catalog | `topics`, `topic_profiles`, `publishers`, `sources`, `topic_sources` |
| Coverage | `documents` (canonical URL hash, text policy), `chunks` (text, vector, tsvector) |
| Editorial | `editions` (one per topic and day), `stories`, `story_documents`, `notes`, `note_versions`, `citations`, `claims`, `claim_checks`, `approvals` |
| Operations | `agent_runs`, `llm_calls`, `ask_requests`, `rate_limits`, `eval_runs` |

Migrations are hand-written, checked by a drift test, and within a release they only add, so the previous image still runs on the new schema during a deploy or a rollback. LangGraph's checkpoints and Procrastinate's queue live in their own schemas.

## Evals

Thirty questions over 40 fictional notes: fictional, so the set tests the mechanics without reproducing anyone's reporting or inventing news about real people. Every pull request scores retrieval without a model against `evals/baseline.json`; the worker runs the set nightly with the Ask model and a judge from another model family, and records the scores.

## Deployment

One VPS runs everything with Docker Compose: a Cloudflare Tunnel, Caddy, the Astro site, the API, the worker (Procrastinate on the same Postgres, so no broker) and Postgres. No container publishes a port. `cloudflared` connects out to Cloudflare, which holds the certificate, and Caddy sends `/api` to the API and the rest to the site, so the stack can share a server with other services and the server's address stays private ([ADR 0002](adr/0002-cloudflare-tunnel.md)). Each container has a memory limit; logs rotate. A merge to `main` that passes CI builds both images, pushes them to GHCR and runs `deploy.sh` over SSH: pull, migrate, start, reload Caddy's config, check the health endpoint through Caddy, and redeploy the previous tag if anything fails. Postgres is dumped nightly with 7 copies kept, and `restore-check.sh` proves the newest dump restores.

Self-hosted Langfuse needs ClickHouse, Redis and object storage, more than a 4 GB server can spare, so tracing uses Langfuse Cloud's free plan.

## Sign-in

The editor signs in through Cloudflare Access ([ADR 0003](adr/0003-sign-in-and-reader-accounts.md)), which stands in front of `/admin` and the admin API and sends each request on with a signed token. The API checks that token itself (signature against the team's published keys, audience, issuer, expiry) rather than trusting a path rule at the edge, and records the editor's email with every decision. Our code never handles the editor's password or code, and Cloudflare logs every sign-in. The cost is a second sign-in system next to readers' accounts, and a dependency on Access being up; without it, `dan review` on the server still decides.

Readers sign in with a six-digit code or a link, sent together by email through Resend; there are no passwords to store or leak, and the email is the account. The code works when the email is read on another device; the link carries its token in the URL fragment, which never reaches the server's logs, and is spent only by pressing a button, so mail scanners that open links do not use it up. Codes and session tokens are stored as SHA-256 digests. The session is an HttpOnly cookie, so no script can read it, with SameSite=Lax plus a check that changes come from the site's own origin. Sign-in emails are limited per address, per hashed IP and per day, below Resend's free 100 a day, and Cloudflare Turnstile stands in front of the form, since a sign-in form is an easy way to make a service email strangers. An account holds an email, the topics followed and topic suggestions; signed out, topics stay in the browser as before, and the first sign-in merges them in. Astro's middleware asks the API who is signed in only when the session cookie is present, so anonymous visits cost nothing extra.

## The site

Astro renders pages on the server; React islands handle the interactive parts: the topic picker, the daily feed, citation chips, Ask and the admin page. UI components take props and never fetch. The API client is generated from FastAPI's OpenAPI schema, and CI fails when either drifts. The fonts DESIGN.md names are downloaded at build time and served from our own origin, so a visit sends nothing to Google.
