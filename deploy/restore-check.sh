#!/usr/bin/env bash
# Restore the newest dump into a scratch database, count what it holds, then drop it.
# The live database is not touched. README, Backups, has the full restore.
set -euo pipefail
cd "$(dirname "$0")"

export TAG
TAG=$(cat .deployed)
dump=$(ls -1t backups/dailyainotes-*.dump | head -n 1)
db=(docker compose -f compose.prod.yml exec -T db)

"${db[@]}" dropdb -U dan --if-exists restore_check
"${db[@]}" createdb -U dan restore_check
"${db[@]}" pg_restore -U dan -d restore_check --no-owner --exit-on-error < "$dump"
"${db[@]}" psql -U dan -d restore_check -At -c \
  "SELECT 'documents ' || count(*) FROM documents
   UNION ALL SELECT 'notes ' || count(*) FROM notes
   UNION ALL SELECT 'migration ' || version_num FROM alembic_version"
"${db[@]}" dropdb -U dan restore_check
echo "restored $dump"
