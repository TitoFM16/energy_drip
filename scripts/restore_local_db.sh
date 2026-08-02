#!/usr/bin/env bash
# Restores a dump produced by backup_local_db.sh into a *new* database on
# the local Docker Compose Postgres, so restoring never touches the real
# dev database by accident. See docs/backup-and-recovery.md.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup-file> [target-db-name]" >&2
  exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-medical_platform_restore_test}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

echo "Dropping and recreating ${TARGET_DB}..."
docker compose exec -T postgres psql -U medical -d postgres \
  -c "DROP DATABASE IF EXISTS ${TARGET_DB};"
docker compose exec -T postgres psql -U medical -d postgres \
  -c "CREATE DATABASE ${TARGET_DB};"

echo "Restoring ${BACKUP_FILE} into ${TARGET_DB}..."
docker compose exec -T postgres pg_restore -U medical -d "$TARGET_DB" --no-owner \
  < "$BACKUP_FILE"

echo "Done. Verify row counts, e.g.:"
echo "  docker compose exec -T postgres psql -U medical -d ${TARGET_DB} -c \"SELECT count(*) FROM patients;\""
echo "Drop it when done: docker compose exec -T postgres psql -U medical -d postgres -c \"DROP DATABASE ${TARGET_DB};\""
