#!/usr/bin/env bash
# Restore the HRMS database from a backup produced by ./scripts/backup.sh
#
#   ./scripts/restore.sh var/backups/hrms-20260711T020000Z.dump hrms_restored
#
# The target database is REQUIRED and must not be the live one. Restoring over a live
# database is how a bad restore turns a recoverable incident into an unrecoverable one:
# restore beside it, verify, then cut over.
set -euo pipefail

DUMP="${1:?usage: restore.sh <dump-file> <target-db>}"
TARGET="${2:?usage: restore.sh <dump-file> <target-db>}"
: "${DATABASE_URL:?DATABASE_URL must be set}"

PG_URL="$(printf '%s' "$DATABASE_URL" | sed -E 's#\+(asyncpg|psycopg2)##')"

# Split the query string off FIRST. A libpq URL may carry `?host=/var/run/postgresql`,
# whose value contains slashes — a greedy "last path segment" regex over the whole URL
# picks a directory out of that parameter instead of the database name, and the
# overwrite guard below then silently fails open. Found by running this script.
BASE="${PG_URL%%\?*}"                       # postgresql://user@host/dbname
QUERY=""
case "$PG_URL" in *\?*) QUERY="?${PG_URL#*\?}" ;; esac
LIVE_DB="${BASE##*/}"                       # dbname
PREFIX="${BASE%/*}"                         # postgresql://user@host

ADMIN_URL="${PREFIX}/postgres${QUERY}"

if [ -z "$LIVE_DB" ] || [ "$TARGET" = "$LIVE_DB" ]; then
  echo "[restore] refusing to restore over the live database ('$LIVE_DB')." >&2
  echo "[restore] restore into a new database, verify it, then cut over." >&2
  exit 1
fi

echo "[restore] verifying archive before touching anything"
pg_restore --list "$DUMP" > /dev/null

echo "[restore] creating target database '$TARGET'"
psql --dbname="$ADMIN_URL" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$TARGET\""
psql --dbname="$ADMIN_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$TARGET\""

TARGET_URL="${PREFIX}/${TARGET}${QUERY}"
echo "[restore] restoring $DUMP -> $TARGET"
pg_restore --dbname="$TARGET_URL" --no-owner --exit-on-error "$DUMP"

echo "[restore] verifying"
psql --dbname="$TARGET_URL" -At -c "SELECT 'alembic head: '||version_num FROM alembic_version"
psql --dbname="$TARGET_URL" -At -c "SELECT 'employees: '||count(*) FROM employees"
echo "[restore] done. Verify the data, then repoint DATABASE_URL at '$TARGET'."
