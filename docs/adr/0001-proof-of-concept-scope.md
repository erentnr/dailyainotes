# 1. Build a proof of concept first

- Status: Accepted
- Date: 2026-10-12
- Decided by: Eren

## Context

The original brief describes a production-grade, multi-user system: accounts, a per-user preference memory, custom topics, a full admin review queue, an MCP server, a provisioning script, offsite backups and monitoring. It must run on one small VPS and use only the free tiers of outside services. Planned that way, the pipeline would not be visible end to end until late in a twelve-milestone build.

## Decision

Build a proof of concept that optimizes for a working, demoable end-to-end pipeline, not production completeness.

**Keep**

- The LangGraph editorial graphs: Topic Planner, Scout with clustering, Researcher, Writer, and the Fact-checker loop.
- Human approval as a LangGraph interrupt.
- Hybrid retrieval (Postgres full text and pgvector, merged by reciprocal rank fusion), and Ask the notes with citations.
- A router over free LLM providers, with fallbacks.
- Local embeddings.
- A small eval set of about 30 questions, run in CI.
- Langfuse Cloud tracing.
- FastAPI and Astro.
- Docker Compose deployment to the VPS through GitHub Actions.
- The public How it works page.

**Simplify**

- No user accounts or sign-in. Visitors pick topics from a fixed catalog of 10 to 15. Their choice is stored in the browser, and the daily page filters notes by topic.
- Ask the notes is rate-limited per IP, to protect the free model quotas.
- Admin access is a single secret token. You approve drafts with the CLI or a minimal page, not a full review UI.
- Operations are a nightly `pg_dump` and a setup section in the README. No Ansible.
- CI runs on Python 3.14 only.

**Defer** (listed under Next steps in the README)

- Custom topics
- User accounts and the preference memory
- The full admin UI
- The MCP server

## Consequences

- The build has seven milestones instead of twelve, and the pipeline goes live on the VPS at the fourth.
- This replaces three earlier plan choices:
  - Voyage embeddings become a local model.
  - Magic-link sign-in with invite codes is removed.
  - The full review UI becomes the CLI or a minimal page.
- Notes are still written once per topic per day. Cost still grows with the number of topics, not visitors.
- Ranking is per topic only. The design's feedback buttons, custom-topic and delivery-time screens wait for accounts.
- To fit on a small VPS, the plan's default embedding model is small and English-only, so the catalog uses English-language sources.
- Backups live on the same disk as the database until offsite backups are added.
