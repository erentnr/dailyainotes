# 5. An MCP server for the published notes

- Status: Accepted; amends [ADR 0001](0001-proof-of-concept-scope.md)
- Date: 2026-10-17
- Decided by: Eren

## Context

ADR 0001 deferred the MCP server with the rest of the original brief's production features. The notes are public, Ask already searches them, and an assistant that can read cited, fact-checked notes shows what the project is for. The owner asked for it after phase 2's first part was deployed.

## Decision

**A public, read-only MCP server at `https://dailyainotes.com/api/mcp`,** over Streamable HTTP, with three tools:

- `list_topics`: the active topics and how many notes each has.
- `search_notes`: Ask's hybrid search over published notes, with optional topics and days. Only strong matches come back, by Ask's rule; none means the notes don't cover the question.
- `get_note`: one note with its citations: the publishers' titles, links and the quotes of at most 25 words the site shows.

**Served by the API, not a separate process:** search needs the embedding model the API already holds for Ask, and a second container would load it again. The SDK (`mcp` 2.3) is imported only by `api/`.

**No sign-in, and no model calls:** the tools return what the site shows anyone. Each request is counted per hashed IP (300 a day) and in total (3,000 a day), in the table Ask uses.

**Stateless, with JSON answers:** each request stands alone, so nothing is kept between requests and the tunnel has nothing to stream. The Host header must be the site's own, against DNS rebinding.

**Kept out of Langfuse:** the SDK marks tool calls with `gen_ai` attributes, which Langfuse would export by default; Langfuse traces model calls only.

## Consequences

- Assistants that speak MCP (Claude, among others) can search and cite the notes; the README shows how to add the server.
- The API counts MCP requests in `rate_limits`, purged after a day like Ask's counts.
- The public API rule holds: the tools show nothing internal (no scores, models or costs).
- Custom topics and the full review UI stay deferred.
