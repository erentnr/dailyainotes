#!/usr/bin/env bash
# Deploy one image tag: pull, migrate, start, check through Caddy; on failure, redeploy the
# previous tag. Migrations only add (INTENT.md), so the previous image runs on the new schema.
# Usage, in /srv/dailyainotes: ./deploy.sh <tag>. The deploy workflow runs it over SSH.
set -euo pipefail
cd "$(dirname "$0")"

tag=${1:?usage: deploy.sh <tag>}
previous=$(cat .deployed 2>/dev/null || true)
image=$(grep '^IMAGE=' .env | cut -d= -f2-)
compose=(docker compose -f compose.prod.yml)

# One && chain: bash ignores `set -e` inside a function called from `if`.
# shellcheck disable=SC2016 # $DOMAIN in single quotes expands in Caddy's container.
up() {
  export TAG=$1
  "${compose[@]}" pull --quiet api worker web &&
    "${compose[@]}" run --rm api dan db upgrade &&
    "${compose[@]}" up -d --wait --remove-orphans &&
    # Through Caddy to the API and the database, inside Docker. Cloudflare's side is not checked
    # here: a rollback cannot fix it (ADR 0002).
    "${compose[@]}" exec -T caddy sh -c \
      'for i in 1 2 3 4 5; do wget -qO- --header "Host: $DOMAIN" http://localhost/api/v1/health && exit; sleep 2; done; exit 1' &&
    echo
}

if up "$tag"; then
  echo "$tag" > .deployed
  # This project's images except this tag and the previous one; a rollback further back pulls
  # its image again. Other images are left alone: the server may run other projects.
  for repo in "$image" "$image-web"; do
    docker image ls --format '{{.Repository}}:{{.Tag}}' "$repo" |
      grep -vxF -e "$repo:$tag" -e "$repo:$previous" |
      xargs -r docker image rm > /dev/null || true
  done
  echo "deployed $tag"
else
  echo "deploy of $tag failed" >&2
  if [[ -n $previous && $previous != "$tag" ]]; then
    echo "rolling back to $previous" >&2
    up "$previous"
  fi
  exit 1
fi
