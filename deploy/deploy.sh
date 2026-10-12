#!/usr/bin/env bash
# Deploy one image tag: pull, migrate, start, check through Caddy; on failure, redeploy the
# previous tag. Migrations only add (INTENT.md), so the previous image runs on the new schema.
# Usage, in /srv/dailyainotes: ./deploy.sh <tag>. The deploy workflow runs it over SSH.
set -euo pipefail
cd "$(dirname "$0")"

tag=${1:?usage: deploy.sh <tag>}
previous=$(cat .deployed 2>/dev/null || true)
domain=$(grep '^DOMAIN=' .env | cut -d= -f2-)
compose=(docker compose -f compose.prod.yml)

# One && chain: bash ignores `set -e` inside a function called from `if`.
up() {
  export TAG=$1
  "${compose[@]}" pull --quiet api worker &&
    "${compose[@]}" run --rm api dan db upgrade &&
    "${compose[@]}" up -d --wait --remove-orphans &&
    # As a visitor reaches it: DNS, the certificate, Caddy, the API and the database.
    curl -fsS --retry 10 --retry-delay 3 --retry-all-errors "https://$domain/api/v1/health" &&
    echo
}

if up "$tag"; then
  echo "$tag" > .deployed
  # Unused images older than three days; a rollback pulls its image again.
  docker image prune -af --filter "until=72h" > /dev/null
  echo "deployed $tag"
else
  echo "deploy of $tag failed" >&2
  if [[ -n $previous && $previous != "$tag" ]]; then
    echo "rolling back to $previous" >&2
    up "$previous"
  fi
  exit 1
fi
