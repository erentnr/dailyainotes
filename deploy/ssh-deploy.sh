#!/usr/bin/env bash
# The forced command of the deploy workflow's SSH key: deploys a commit of main with that commit's
# deploy/ files. Installed by root as /usr/local/bin/dailyainotes-deploy and named in deploy's
# authorized_keys (README, Deploy):
#
#   restrict,command="/usr/local/bin/dailyainotes-deploy" ssh-ed25519 AAAA... dailyainotes-deploy
#
# so the key can't open a shell or copy files, and a leaked key can only redeploy main. The command
# the client sends (SSH_ORIGINAL_COMMAND) is the commit. It runs as deploy, so it can't replace
# itself: after changing it, install it again as root.
set -euo pipefail

sha=${SSH_ORIGINAL_COMMAND:-${1:-}}
if [[ ! $sha =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: dailyainotes-deploy <40 character commit sha>" >&2
  exit 2
fi

cd /srv/dailyainotes
# src is a clone of the public repository, used only for this.
git -C src fetch --quiet origin main
if ! git -C src merge-base --is-ancestor "$sha" origin/main 2> /dev/null; then
  echo "$sha is not on main" >&2
  exit 1
fi
git -C src archive "$sha" deploy | tar -x --strip-components=1
exec ./deploy.sh "$sha"
