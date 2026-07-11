#!/usr/bin/env bash
# Back up the HRMS database.
#
# Custom format (-Fc), compressed: it is selectively restorable (a single table can be
# pulled out of it) and pg_restore can verify it WITHOUT touching a database, which is
# what makes the nightly integrity check below possible.
#
#   ./scripts/backup.sh                      # -> ./var/backups/hrms-<utc-timestamp>.dump
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh
#
# Cron (nightly at 02:00, keeping 14 days):
#   0 2 * * *  cd /srv/hrms/backend && ./scripts/backup.sh >> var/logs/backup.log 2>&1
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
BACKUP_DIR="${BACKUP_DIR:-var/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

# pg_dump speaks libpq, not SQLAlchemy: strip the +asyncpg/+psycopg2 driver suffix.
PG_URL="$(printf '%s' "$DATABASE_URL" | sed -E 's#\+(asyncpg|psycopg2)##')"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/hrms-$STAMP.dump"

echo "[backup] dumping -> $OUT"
pg_dump --dbname="$PG_URL" --format=custom --compress=6 --file="$OUT"

# Verify the dump is readable before trusting it. A backup you have never read is a
# hypothesis, not a backup — this catches truncation and corruption the night it
# happens rather than during an incident.
echo "[backup] verifying archive integrity"
pg_restore --list "$OUT" > /dev/null
echo "[backup] ok: $(du -h "$OUT" | cut -f1)"

echo "[backup] pruning archives older than ${RETENTION_DAYS}d"
find "$BACKUP_DIR" -name 'hrms-*.dump' -mtime "+$RETENTION_DAYS" -print -delete
