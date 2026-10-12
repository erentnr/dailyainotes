#!/usr/bin/env bash
# Dump the database and keep the newest 7 dumps. The server's crontab runs it nightly:
#   30 0 * * * /srv/dailyainotes/backup.sh
# restore-check.sh proves the newest dump restores.
set -euo pipefail
cd "$(dirname "$0")"

export TAG
TAG=$(cat .deployed)
mkdir -p backups
file="backups/dailyainotes-$(date -u +%Y-%m-%dT%H%MZ).dump"
docker compose -f compose.prod.yml exec -T db \
  pg_dump -U dan -d dailyainotes --format=custom > "$file.partial"
mv "$file.partial" "$file"
ls -1t backups/dailyainotes-*.dump | tail -n +8 | xargs rm -f --
echo "$file"
