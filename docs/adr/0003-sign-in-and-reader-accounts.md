# 3. Editor sign-in through Cloudflare Access, and reader accounts

- Status: Accepted; amended by [ADR 0004](0004-ask-needs-an-account.md) (Ask needs an account, 2026-10-16)
- Date: 2026-10-15
- Decided by: Eren

## Context

Phase 1 (ADR 0001) had no accounts, and the editor reached /admin with one shared secret, `ADMIN_TOKEN`, pasted into the page. Once the site was live, the owner judged it not ready for real readers:

- The token was one secret for everything. It sat in the browser's session storage, where any script injected into the site could read it. It never expired, had no second factor and no lockout, and revoking it meant editing the server's `.env` and restarting.
- An approval did not record who made it, so a second editor would have needed the same secret.
- Readers could not sign in at all. Their topics lived in one browser.

The owner looked at it as a product: reading and Ask stay open to everyone, and an account must give a reader something worth signing in for.

## Decision

**The editor signs in through Cloudflare Access.** An Access application covers `/admin` and `/api/v1/admin`, and allows only the editor's email, with an emailed one-time PIN as the way in. Access adds a signed token to every request it lets through (`Cf-Access-Jwt-Assertion`). The API checks it against the team's published keys, the application's audience tag and the team's issuer, and refuses anything else, so a request that did not pass Access, or a forged header, gets 401. The token's email is recorded with each decision on a note or a topic plan. `ADMIN_TOKEN` is removed. `dan review` on the server still works, recorded as "dan review".

**Readers can have accounts** (M8). An account gives two things:

- **Their topics on every device.** Signed out, topics stay in the browser as before. At the first sign-in, the browser's picks merge into the account.
- **Topic suggestions** (M9). A reader suggests a topic; the editor accepts or declines it at /admin. Accepting runs the Topic Planner, and the plan is reviewed at /admin like a note.

Readers sign in with an emailed code or link: no passwords are stored, and the email is the account. Resend's free plan sends the email. Sessions are random tokens in an HttpOnly, Secure, SameSite=Lax cookie, stored only as a hash.

Not chosen for now: a daily email of the reader's notes, and "more like this" feedback with a preference memory. They stay in the README's Next steps, with the MCP server, the rest of the full review UI, and offsite backups and monitoring.

## Consequences

- No password or sign-in code for the editor is ever handled by our code; Access gives the editor a second check before the page loads, and audit logs in Cloudflare. Zero Trust's free plan covers 50 users (third-party pricing pages, 2026-10-15; Cloudflare's own pages did not state it).
- The admin depends on Cloudflare Access being up, as the site already depends on the tunnel (ADR 0002). Without Access settings, admin is off and `dan review` is the way to decide.
- There are two sign-in systems: Access for the editor and email codes for readers. A reader's session never grants admin.
- The API checks Access's token itself instead of trusting Cloudflare alone, since a path rule at the edge is the only thing between the internet and the admin API otherwise.
- Accounts bring personal data: emails. The site gets a privacy page and a way to delete an account, sign-in emails are rate-limited, and the domain gets SPF, DKIM and DMARC records for its email.
- Each accepted suggestion adds a topic, and every active topic spends model quota. The daily cap stays at 15 drafts, 2 per topic, so the editor decides how many topics are active.
- This amends ADR 0001, which deferred accounts and kept admin to one token.
