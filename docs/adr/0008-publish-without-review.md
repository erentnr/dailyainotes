# 8. Notes and topic plans publish without a person's review

- Status: Accepted; amends [ADR 0001](0001-proof-of-concept-scope.md), [ADR 0003](0003-sign-in-and-reader-accounts.md) and [ADR 0006](0006-readers-add-topics.md)
- Date: 2026-10-22
- Decided by: Eren

## Context

Since the start (2026-10-12), every note and every topic plan waited for the owner's approval in a LangGraph interrupt. When the owner did not review for a few days, the site stopped changing: on 2026-10-21 it still showed 18 October while 36 finished drafts waited. The owner wants the pipeline to publish on its own.

## Decision

**Every note that finishes the story graph is published.** After the citation check, the fact-check and at most two rewrites, the graph publishes the note and indexes it for Ask, with no pause. Its claims' verdicts are published with it, so a note with weak or unsupported claims shows them in its badge and its trail. The decision is recorded as made by `automatic`.

**A topic plan decides itself.** A plan that keeps at least three readable, on-topic news feeds makes the topic live (and, for a topic a reader added, joins it to their topics). A plan with fewer is rejected, and a reader who added the topic sees why.

**The editor can withdraw a published note.** At /admin, or with `dan review withdraw note-<id>`, a note leaves the site, Ask and the MCP server. The withdrawal is kept with the note's decisions, with who did it and why.

**The drafts waiting on 2026-10-22 were published** under this rule, before the change deployed.

## Consequences

- The site's copy no longer says a person approves each note; it says the note was published after the checks, and how it was checked.
- The approval queue at /admin becomes a list of the latest published notes, each with Withdraw. The topic plans page and the approve and reject decisions in the API and `dan review` go.
- Off-topic or wrongly checked notes reach readers until someone withdraws them. The Scout topic check, the citation check, the fact-check and the badge are what stands between a draft and readers.
- Migration 0014 lets a note be `withdrawn` and a decision be `withdraw`.
