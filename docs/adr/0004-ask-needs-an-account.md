# 4. Ask needs an account

- Status: Accepted; amends [ADR 0003](0003-sign-in-and-reader-accounts.md)
- Date: 2026-10-16
- Decided by: Eren

## Context

ADR 0003 kept reading and Ask open to everyone, with Ask limited to 10 questions per hashed IP and 100 in total a day. Every answer costs a model call on a free quota that the nightly run needs too, and a per-IP limit is easy to get around and unfair to people who share a connection. Accounts now exist (M8), and the owner wants Ask to be one of the things worth signing in for.

## Decision

**Asking needs a signed-in reader.** `POST /api/v1/ask` answers 401 without a session; the site shows a signed-out visitor what Ask does and a way to sign in, and keeps the question they typed through sign-in. Reading stays open to everyone.

**Limits:** 10 questions a day per reader, 30 a day per hashed IP (a household or an office may have several accounts on one connection), and 200 a day in total.

**Questions belong to the reader.** The Ask log keeps the reader with each question, next to the question, the notes the answer cited and the hashed IP, for 30 days. Deleting the account deletes its questions.

## Consequences

- An account now holds an email, the topics followed, topic suggestions and its questions to Ask from the last 30 days. The privacy page, INTENT.md and docs/design.md say so.
- Where sign-in is off (no `RESEND_API_KEY`), nobody can ask. The CLI (`dan ask`) and the evals call Ask directly and are not affected.
- Linked questions make a "your questions" list on the account page possible later; it is not built.
