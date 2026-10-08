#!/usr/bin/env bash
# WP-004: disposable PostgreSQL harness for Alembic recovery validation.

set -o pipefail

RUN_ID="$(date +%s)_$$"
CONTAINER_NAME="business-automation-alembic-wp004-${RUN_ID}"
DB_ADMIN="wp004_admin_${RUN_ID}"
DB_PASSWORD="wp004_admin_pass_${RUN_ID}"
FRESH_DB="wp004_fresh_${RUN_ID}"
LEGACY_DB="wp004_legacy_${RUN_ID}"
AMBIGUOUS_DB="wp004_ambiguous_${RUN_ID}"
PORT=""

cleanup() {
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

fail() {
    echo "ERROR: $1"
    exit 1
}

create_db() {
    local db_name="$1"
    docker exec         -e PGPASSWORD="$DB_PASSWORD"         "$CONTAINER_NAME"         createdb -h 127.0.0.1 -U "$DB_ADMIN" "$db_name"         >/dev/null 2>&1
    return $?
}

psql_value() {
    local db_name="$1"
    local sql="$2"
    docker exec         -e PGPASSWORD="$DB_PASSWORD"         "$CONTAINER_NAME"         psql -h 127.0.0.1 -U "$DB_ADMIN" -d "$db_name"         -v ON_ERROR_STOP=1 -A -t -F '|' -c "$sql" 2>/dev/null
}

trap cleanup EXIT INT TERM

if ! command -v docker >/dev/null 2>&1; then
    fail "Docker is not available."
fi

HEADS_OUTPUT="$(uv run alembic heads 2>&1)"
HEADS_EXIT=$?
if [ "$HEADS_EXIT" -ne 0 ]; then
    fail "Unable to inspect Alembic heads: $HEADS_OUTPUT"
fi

HEAD_COUNT="$(printf '%s\n' "$HEADS_OUTPUT" | grep -c '(head)')"
if [ "$HEAD_COUNT" -ne 1 ]; then
    fail "Expected exactly one Alembic head, found ${HEAD_COUNT}: $HEADS_OUTPUT"
fi

HEAD_REV="$(printf '%s\n' "$HEADS_OUTPUT" | awk '/\(head\)/ {print $1; exit}')"
if [ -z "$HEAD_REV" ]; then
    fail "Unable to determine Alembic head revision."
fi

CONTAINER_OUTPUT="$(
    docker run -d         --name "$CONTAINER_NAME"         --rm         -e POSTGRES_USER="$DB_ADMIN"         -e POSTGRES_PASSWORD="$DB_PASSWORD"         -e POSTGRES_DB=postgres         -p 127.0.0.1::5432         postgres:17 2>&1
)"
DOCKER_RUN_EXIT=$?
if [ "$DOCKER_RUN_EXIT" -ne 0 ]; then
    fail "Unable to start disposable PostgreSQL container: $CONTAINER_OUTPUT"
fi

WAITED=0
MAX_WAIT=60
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    docker exec "$CONTAINER_NAME"         pg_isready -h 127.0.0.1 -U "$DB_ADMIN" -d postgres         >/dev/null 2>&1
    if [ "$?" -eq 0 ]; then
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    fail "PostgreSQL did not become ready within ${MAX_WAIT}s."
fi

PORT_LINE="$(docker port "$CONTAINER_NAME" 5432/tcp 2>/dev/null | head -n 1)"
PORT="${PORT_LINE##*:}"
if [ -z "$PORT" ] || ! printf '%s' "$PORT" | grep -Eq '^[0-9]+$'; then
    fail "Unable to determine the disposable PostgreSQL host port."
fi

# Scenario A: fresh database.
create_db "$FRESH_DB"
if [ "$?" -ne 0 ]; then
    fail "Unable to create fresh validation database."
fi

FRESH_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${PORT}/${FRESH_DB}"

FRESH_UPGRADE_OUTPUT="$(DATABASE_URL="$FRESH_URL" uv run alembic upgrade head 2>&1)"
FRESH_UPGRADE_EXIT=$?
if [ "$FRESH_UPGRADE_EXIT" -ne 0 ]; then
    fail "Fresh database upgrade failed: $FRESH_UPGRADE_OUTPUT"
fi

FRESH_CURRENT="$(DATABASE_URL="$FRESH_URL" uv run alembic current 2>&1)"
FRESH_CURRENT_EXIT=$?
if [ "$FRESH_CURRENT_EXIT" -ne 0 ] || ! printf '%s\n' "$FRESH_CURRENT" | grep -q "$HEAD_REV"; then
    fail "Fresh database is not at expected head ${HEAD_REV}: $FRESH_CURRENT"
fi

FRESH_CHECK="$(DATABASE_URL="$FRESH_URL" uv run alembic check 2>&1)"
FRESH_CHECK_EXIT=$?
if [ "$FRESH_CHECK_EXIT" -ne 0 ]; then
    fail "Fresh database Alembic check reported drift: $FRESH_CHECK"
fi

FRESH_LEGACY_COMPANY_COUNT="$(
    psql_value "$FRESH_DB"         "SELECT COUNT(*) FROM companies WHERE slug = 'legacy-workspace';"
)"
if [ "$?" -ne 0 ] || [ "$FRESH_LEGACY_COMPANY_COUNT" != "0" ]; then
    fail "Fresh database unexpectedly contains Legacy Workspace."
fi

echo "FRESH_DATABASE_UPGRADE_OK"

# Scenario B: synthetic legacy baseline.
create_db "$LEGACY_DB"
if [ "$?" -ne 0 ]; then
    fail "Unable to create legacy validation database."
fi

LEGACY_SETUP_SQL="
CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    source VARCHAR(50) NOT NULL,
    interest VARCHAR(255),
    status VARCHAR(30) NOT NULL
);
INSERT INTO leads (id, name, phone, source, interest, status)
VALUES (41, 'Legacy Lead', '11999999999', 'legacy-import', 'automation', 'new');
"

docker exec     -e PGPASSWORD="$DB_PASSWORD"     "$CONTAINER_NAME"     psql -h 127.0.0.1 -U "$DB_ADMIN" -d "$LEGACY_DB"     -v ON_ERROR_STOP=1 -c "$LEGACY_SETUP_SQL"     >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "Unable to create synthetic legacy fixture."
fi

LEGACY_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${PORT}/${LEGACY_DB}"

LEGACY_STAMP_OUTPUT="$(
    DATABASE_URL="$LEGACY_URL" uv run alembic stamp 7c83bbc2b9f7 2>&1
)"
LEGACY_STAMP_EXIT=$?
if [ "$LEGACY_STAMP_EXIT" -ne 0 ]; then
    fail "Unable to stamp synthetic legacy database: $LEGACY_STAMP_OUTPUT"
fi

LEGACY_UPGRADE_OUTPUT="$(
    DATABASE_URL="$LEGACY_URL" uv run alembic upgrade head 2>&1
)"
LEGACY_UPGRADE_EXIT=$?
if [ "$LEGACY_UPGRADE_EXIT" -ne 0 ]; then
    fail "Legacy baseline upgrade failed: $LEGACY_UPGRADE_OUTPUT"
fi

LEGACY_CORE="$(
    psql_value "$LEGACY_DB"         "SELECT id, name, phone, source, interest, status FROM leads WHERE id = 41;"
)"
if [ "$LEGACY_CORE" != "41|Legacy Lead|11999999999|legacy-import|automation|new" ]; then
    fail "Legacy lead business data was not preserved: $LEGACY_CORE"
fi

LEGACY_TIMESTAMPS="$(
    psql_value "$LEGACY_DB"         "SELECT (created_at IS NOT NULL)::int, (updated_at IS NOT NULL)::int FROM leads WHERE id = 41;"
)"
if [ "$LEGACY_TIMESTAMPS" != "1|1" ]; then
    fail "Legacy lead timestamps were not populated: $LEGACY_TIMESTAMPS"
fi

LEGACY_COMPANY_ID="$(
    psql_value "$LEGACY_DB"         "SELECT company_id FROM leads WHERE id = 41;"
)"
if [ -z "$LEGACY_COMPANY_ID" ] || ! printf '%s' "$LEGACY_COMPANY_ID" | grep -Eq '^[0-9]+$'; then
    fail "Legacy lead did not receive a valid company_id."
fi

LEGACY_COMPANY_COUNT="$(
    psql_value "$LEGACY_DB"         "SELECT COUNT(*) FROM companies WHERE name = 'Legacy Workspace' AND slug = 'legacy-workspace';"
)"
if [ "$LEGACY_COMPANY_COUNT" != "1" ]; then
    fail "Expected exactly one Legacy Workspace company, got ${LEGACY_COMPANY_COUNT}."
fi

LEGACY_FK_COUNT="$(
    psql_value "$LEGACY_DB"         "SELECT COUNT(*) FROM leads l JOIN companies c ON c.id = l.company_id WHERE l.id = 41;"
)"
if [ "$LEGACY_FK_COUNT" != "1" ]; then
    fail "Legacy lead company foreign key is invalid."
fi

LEGACY_CURRENT="$(DATABASE_URL="$LEGACY_URL" uv run alembic current 2>&1)"
LEGACY_CURRENT_EXIT=$?
if [ "$LEGACY_CURRENT_EXIT" -ne 0 ] || ! printf '%s\n' "$LEGACY_CURRENT" | grep -q "$HEAD_REV"; then
    fail "Legacy database is not at expected head ${HEAD_REV}: $LEGACY_CURRENT"
fi

echo "LEGACY_BASELINE_UPGRADE_OK"

# Scenario C: ambiguous company mapping must be rejected.
create_db "$AMBIGUOUS_DB"
if [ "$?" -ne 0 ]; then
    fail "Unable to create ambiguous-mapping validation database."
fi

AMBIGUOUS_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${PORT}/${AMBIGUOUS_DB}"

AMBIGUOUS_PREP_OUTPUT="$(
    DATABASE_URL="$AMBIGUOUS_URL" uv run alembic upgrade 4749a8ea474b 2>&1
)"
AMBIGUOUS_PREP_EXIT=$?
if [ "$AMBIGUOUS_PREP_EXIT" -ne 0 ]; then
    fail "Unable to prepare ambiguous-mapping database: $AMBIGUOUS_PREP_OUTPUT"
fi

AMBIGUOUS_SETUP_SQL="
INSERT INTO companies (id, name, slug)
VALUES
    (101, 'Company A', 'company-a'),
    (102, 'Company B', 'company-b');

INSERT INTO leads (id, name, phone, source, interest, status, company_id)
VALUES
    (201, 'Ambiguous Lead', '11888888888', 'legacy-import', NULL, 'new', NULL);
"

docker exec     -e PGPASSWORD="$DB_PASSWORD"     "$CONTAINER_NAME"     psql -h 127.0.0.1 -U "$DB_ADMIN" -d "$AMBIGUOUS_DB"     -v ON_ERROR_STOP=1 -c "$AMBIGUOUS_SETUP_SQL"     >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "Unable to create ambiguous company fixture."
fi

AMBIGUOUS_OUTPUT="$(
    DATABASE_URL="$AMBIGUOUS_URL" uv run alembic upgrade 6db09cfda379 2>&1
)"
AMBIGUOUS_EXIT=$?

if [ "$AMBIGUOUS_EXIT" -eq 0 ]; then
    fail "Ambiguous company mapping unexpectedly succeeded."
fi

if ! printf '%s\n' "$AMBIGUOUS_OUTPUT" | grep -q "Ambiguous company mapping"; then
    fail "Ambiguous company mapping failed for the wrong reason: $AMBIGUOUS_OUTPUT"
fi

AMBIGUOUS_CURRENT="$(DATABASE_URL="$AMBIGUOUS_URL" uv run alembic current 2>&1)"
if ! printf '%s\n' "$AMBIGUOUS_CURRENT" | grep -q "4749a8ea474b"; then
    fail "Ambiguous migration did not roll back cleanly: $AMBIGUOUS_CURRENT"
fi

echo "AMBIGUOUS_COMPANY_MAPPING_REJECTED"
echo "ALEMBIC_RECOVERY_VERIFIED"
