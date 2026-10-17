# 7. "More like this" orders a reader's page

- Status: Accepted; amends [ADR 0001](0001-proof-of-concept-scope.md)
- Date: 2026-10-17
- Decided by: Eren

## Context

ADR 0001 deferred a per-reader preference memory fed by "more like this" and "less like this". Notes are written once per topic and shared by every reader (one edition per topic, then fan-out), so feedback cannot change what is written without spending quota per reader.

## Decision

**Feedback changes the order of a reader's daily page, not what is drafted.** A signed-in reader marks a note "More like this" or "Less like this" on its page. The account keeps the latest 100 marks; each of the day's notes then scores its closeness (cosine, on the vectors notes already have for Ask) to the notes marked "more", less its closeness to those marked "less", and the page leads with the highest. A reader with no marks keeps the usual order, the day's biggest story first.

**It goes with the account.** Deleting the account deletes the marks. Signed out, there are no buttons.

## Consequences

- An account now also holds the notes a reader marked; the privacy page and INTENT.md say so.
- "Not relevant", the design's third button, stays out: "Less like this" covers it.
