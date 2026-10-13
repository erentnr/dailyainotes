# 2. Bring visitors in through a Cloudflare Tunnel

- Status: Accepted
- Date: 2026-10-13
- Decided by: Eren

## Context

The plan put Caddy at the edge: it published ports 80 and 443 and obtained the certificate itself. The production server is shared with other services, and one of them already holds ports 80 and 443, so the stack's Caddy could not start there. The domain's DNS is on Cloudflare.

Three ways were considered:

- **Share the other service's Caddy:** add a site block to its configuration and join the two Docker networks. The least new code, but the site would depend on another project's container and configuration.
- **One Caddy for the whole server,** in its own folder, serving every project. The cleanest setup for a shared server, but it moves the other projects' HTTPS too.
- **A Cloudflare Tunnel:** a `cloudflared` container connects out to Cloudflare, and Cloudflare brings visitors in.

## Decision

Use a Cloudflare Tunnel. The stack runs `cloudflared` next to Caddy and publishes no port. Caddy stays inside on plain HTTP and keeps its jobs: sending `/api` to the API and the rest to the site, compression, security headers, and `www` to the bare domain.

## Consequences

- The stack shares a server without competing for ports, and the server's address does not appear in DNS. `DEPLOY_HOST` became a secret, so CI's public logs do not show it either.
- Cloudflare terminates HTTPS and sees the traffic in clear. Its free plan is enough; the tunnel's token is one more secret in the server's `.env`.
- The visitor's address comes from Cloudflare's `CF-Connecting-IP`, the address that connected to Cloudflare, which Caddy passes to the API as `X-Forwarded-For`. Cloudflare keeps an `X-Forwarded-For` a visitor sends and appends to it, so trusting that header would let anyone pass Ask's per-IP limit (Cloudflare's HTTP headers reference, 2026-10-13).
- Cloudflare buffers a tunnel's responses unless they are `text/event-stream`, which Ask's answers are.
- `deploy.sh` checks health through Caddy inside Docker instead of over the public URL. A fault on Cloudflare's side is not something a rollback can fix, so it no longer triggers one.
- The site depends on Cloudflare being up.
