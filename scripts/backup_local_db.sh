#!/usr/bin/env bash
# Dumps the local Docker Compose Postgres database to a timestamped file
# under ./backups/. This is a *local dev/verification* tool, not a
# production backup strategy — a real deployment needs automated,
# off-host, tested backups from whatever managed Postgres provider is
# chosen (see docs/backup-and-recovery.md), not a developer running this
# by hand. Useful here for: exercising the restore path before trusting
# any backup strategy, and as a manual safety net before a risky local
# migration/data experiment.
set -euo pipefail

cd "$(dirname "$0")/.."

BACKUP_DIR="backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/medical_platform-${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "Dumping medical_platform from the running postgres container to ${BACKUP_FILE}..."
docker compose exec -T postgres pg_dump -U medical -d medical_platform --format=custom \
  > "$BACKUP_FILE"

echo "Done: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"
echo "Restore with: ./scripts/restore_local_db.sh ${BACKUP_FILE} <target-db-name>"
