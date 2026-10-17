# AGENTS.md

Daily AI Notes is an open-source multi-agent RAG application that writes short, cited, fact-checked daily notes on catalog topics: Python 3.14, FastAPI, LangGraph, Postgres 18 with pgvector, and an Astro site. It is a portfolio project in its proof-of-concept phase (docs/adr/0001-proof-of-concept-scope.md), so architecture, code quality, tests and documentation count as much as features.

Read first: INTENT.md (rules & standing tasks) · DESIGN.md (visual system) · MEMORY.md (agent memory) · `.private/MEMORY.md` (private memory, gitignored; read it when it exists). Read INTENT.md and both memory files before any task (Claude Code loads them through the import at the end of this file and through `CLAUDE.local.md`); read DESIGN.md before any UI work. Rules go in INTENT.md and knowledge in the memory files; this file is how to work. Nothing from `.private/` may appear in a committed file, commit message or anything published. Codex and Claude Code both read this file; CLAUDE.md only imports it, so edit this one. Paths and commands named here that don't exist yet are created by the milestones in INTENT.md's standing tasks.

The four principles below come from Andrej Karpathy's observations on LLM coding pitfalls (github.com/multica-ai/andrej-karpathy-skills), adapted to this project. They favor caution over speed: for a typo or an obvious one-liner, use judgment.

## Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- INTENT.md's Working Agreement says to ask rather than guess and to plan before building. In practice: stop at the first ambiguity, offer concrete options with the recommended one first, and put the plan with its checks in front of the owner before writing code.
- Requests can be short and miss a word. Confirm the intent behind them.
- Check scope before building: ADR 0001 defers custom topics and the full admin UI (ADR 0003 brought in accounts, ADR 0005 the MCP server). If a request needs one of them, say so instead of building it.
- Package versions, model IDs, free-tier limits and API behaviour go stale. Check the live source (PyPI, npm, the provider's docs), and record what you verified in MEMORY.md with the source and the date.
- When two idioms both work (ORM or Core query, a graph node or a plain function, an island or a server-rendered page), name the trade-off in one line, pick one, move on.
- If INTENT.md, the memory files, DESIGN.md, an ADR and the request disagree, say so; don't resolve it silently.

## Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features, settings or flags beyond what was asked. A knob nobody can safely turn is not a setting.
- A function before a class, a module before a package. Interfaces only at the seams INTENT.md names: the LLM router, embeddings, source connectors, the reranker.
- A fixed sequence is a function, not an agent. Models are called only where judging text matters: the Topic Planner's profile, Researcher, Writer, claim extraction and verification, the Ask answer. Scout's collect, cluster and rank is code.
- Handle the failures that happen (timeouts, 429s, exhausted free quotas, malformed feeds, model output that fails validation); let impossible ones raise.
- No new dependency when the standard library or an existing one does the job. Phase 1 has no Redis, no vector database and no auth library.
- If 200 lines could be 50, rewrite. Would a senior engineer reviewing this call it overcomplicated?

## Surgical Changes

Touch only what you must. Clean up only your own mess.

- Don't improve adjacent code, comments or formatting. ruff owns formatting; match the existing style everywhere else.
- Unrelated dead code or a smell: mention it, or add it to INTENT.md's standing tasks. Don't fix it in the same change.
- Remove the imports, variables and functions your change made unused; leave pre-existing dead code.
- Never edit a committed migration; a schema change is a new revision that keeps the drift test green, and within a release it only adds.
- Never hand-edit `uv.lock`, `pnpm-lock.yaml` or the generated API client in `web/src/lib/api/`; regenerate them. One step, one commit; no lockfile churn riding along.
- Never touch `.env` or secrets; a new setting goes into `settings.py` and `.env.example` together.
- The test: every changed line traces directly to the request.

## Goal-Driven Execution

Define success criteria. Loop until verified.

- Turn each task into a check:
  - "Fix the bug" → a pytest test that reproduces it, then make it pass.
  - "Add a connector" → tests against a recorded response in `tests/fixtures/<source>/` first.
  - "Change the schema" → a migration that keeps the drift test green.
  - "Change a prompt or a graph" → a graph test with a fake chat model, then `dan evals run`.
  - "Refactor" → tests pass before and after.
- State a short plan before multi-step work:
  ```
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
  ```
- Done means `make check` passes with Postgres running (`make up`); both arrive in M0. A skipped test is not a pass: read the summary line.
- A test that passes on its first run proves little: break the code once and watch it fail.
- Probe how a library or service actually behaves before trusting docs or memory (Ollama Cloud's structured output, OpenRouter's free models, fastembed's resolve), and record the result in MEMORY.md.
- Claims about the live system (free quotas, memory use on the VPS, a deploy) are verified on the real service, not assumed from documentation.
- Report what happened with the output (INTENT.md): paste the summary line of the gate, not "tests pass".
- End every session by updating the memory files (Working and Episodic; private items in `.private/MEMORY.md`) and ticking INTENT.md's standing tasks.

---

**These guidelines are working if** diffs contain only requested changes, code is simple the first time, and clarifying questions come before implementation rather than after mistakes.

@INTENT.md
@MEMORY.md
