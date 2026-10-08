#!/usr/bin/env bash
# WP-006: validate PostgreSQL logical backup and restore using one disposable
# PostgreSQL 17 container and synthetic data only.

set -u
set -o pipefail

RUN_ID="$(date +%s)_$$"
CONTAINER_PREFIX="business-automation-backup-wp006-"
CONTAINER_NAME="${CONTAINER_PREFIX}${RUN_ID}"
DB_ADMIN="wp006_admin_${RUN_ID}"
DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
SOURCE_DB="wp006_source_${RUN_ID}"
RESTORE_DB="wp006_restore_${RUN_ID}"
BACKUP_FILE="/tmp/business-automation-wp006-${RUN_ID}.dump"
PGDUMP_ERR="/tmp/business-automation-wp006-${RUN_ID}.pgdump.err"
PGRESTORE_ERR="/tmp/business-automation-wp006-${RUN_ID}.pgrestore.err"
HOST_PORT=""
HEAD_REV=""

cleanup() {
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi

    rm -f "$BACKUP_FILE" "$PGDUMP_ERR" "$PGRESTORE_ERR" 2>/dev/null || true
}

fail() {
    echo "ERROR: $1"
    exit 1
}

psql_value() {
    local db_name="$1"
    local sql="$2"

    docker exec         -e PGPASSWORD="$DB_PASSWORD"         "$CONTAINER_NAME"         psql         -h 127.0.0.1         -U "$DB_ADMIN"         -d "$db_name"         -v ON_ERROR_STOP=1         -A -t -F '|'         -c "$sql" 2>/dev/null
}

create_db() {
    local db_name="$1"

    docker exec         -e PGPASSWORD="$DB_PASSWORD"         "$CONTAINER_NAME"         createdb         -h 127.0.0.1         -U "$DB_ADMIN"         "$db_name"         >/dev/null 2>&1
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "=== WP-006: PostgreSQL backup/restore drill ==="

# ---------------------------------------------------------------------------
# Preflight before the container.
# ---------------------------------------------------------------------------

command -v docker >/dev/null 2>&1 || fail "Docker is not available."

HEADS_OUTPUT="$(uv run alembic heads 2>&1)"
HEADS_EXIT=$?
if [ "$HEADS_EXIT" -ne 0 ]; then
    fail "Unable to inspect Alembic heads."
fi

HEAD_COUNT="$(printf '%s\n' "$HEADS_OUTPUT" | grep -c '(head)')"
if [ "$HEAD_COUNT" -ne 1 ]; then
    fail "Expected exactly one Alembic head, found $HEAD_COUNT."
fi

HEAD_REV="$(printf '%s\n' "$HEADS_OUTPUT" | awk '/\(head\)/ {print $1; exit}')"
if [ -z "$HEAD_REV" ]; then
    fail "Unable to determine the Alembic head revision."
fi

EXISTING_WP006="$(
    docker ps -a --format '{{.Names}}' 2>/dev/null |
        grep "^$CONTAINER_PREFIX" || true
)"
if [ -n "$EXISTING_WP006" ]; then
    fail "A WP-006 container already exists; inspect it before starting a new run."
fi

REPO_DUMPS="$(
    find . -type f -name 'business-automation-wp006-*.dump' -print -quit 2>/dev/null
)"
if [ -n "$REPO_DUMPS" ]; then
    fail "A WP-006 dump artifact exists inside the repository."
fi

# ---------------------------------------------------------------------------
# Single disposable PostgreSQL 17 container.
# ---------------------------------------------------------------------------

CONTAINER_OUTPUT="$(
    docker run -d         --name "$CONTAINER_NAME"         --rm         -e POSTGRES_USER="$DB_ADMIN"         -e POSTGRES_PASSWORD="$DB_PASSWORD"         -e POSTGRES_DB=postgres         -p 127.0.0.1::5432         postgres:17 2>&1
)"
CONTAINER_EXIT=$?
if [ "$CONTAINER_EXIT" -ne 0 ]; then
    fail "Unable to start the disposable PostgreSQL container."
fi

WAITED=0
MAX_WAIT=60
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    docker exec "$CONTAINER_NAME"         pg_isready -U "$DB_ADMIN" -d postgres         >/dev/null 2>&1
    if [ "$?" -eq 0 ]; then
        break
    fi

    sleep 1
    WAITED=$((WAITED + 1))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "PostgreSQL container did not become ready; recent container logs:"
    docker logs --tail 30 "$CONTAINER_NAME" 2>&1 || true
    fail "PostgreSQL readiness check timed out."
fi

docker exec "$CONTAINER_NAME" pg_dump --version >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "pg_dump is not available inside postgres:17."
fi

docker exec "$CONTAINER_NAME" pg_restore --version >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "pg_restore is not available inside postgres:17."
fi

PORT_LINE="$(docker port "$CONTAINER_NAME" 5432/tcp 2>/dev/null | head -n 1)"
HOST_PORT="${PORT_LINE##*:}"
if [ -z "$HOST_PORT" ] || ! printf '%s' "$HOST_PORT" | grep -Eq '^[0-9]+$'; then
    fail "Unable to determine the random host port."
fi

# ---------------------------------------------------------------------------
# Source database: migrate to head and insert the exact synthetic fixture.
# ---------------------------------------------------------------------------

create_db "$SOURCE_DB"
if [ "$?" -ne 0 ]; then
    fail "Unable to create the source database."
fi

SOURCE_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${HOST_PORT}/${SOURCE_DB}"

SOURCE_UPGRADE="$(
    DATABASE_URL="$SOURCE_URL" uv run alembic upgrade head 2>&1
)"
SOURCE_UPGRADE_EXIT=$?
if [ "$SOURCE_UPGRADE_EXIT" -ne 0 ]; then
    fail "Alembic upgrade failed on the source database."
fi

SOURCE_CURRENT="$(
    DATABASE_URL="$SOURCE_URL" uv run alembic current 2>&1
)"
SOURCE_CURRENT_EXIT=$?
if [ "$SOURCE_CURRENT_EXIT" -ne 0 ] ||
   ! printf '%s\n' "$SOURCE_CURRENT" | grep -q "$HEAD_REV"; then
    fail "Source database is not at the expected Alembic head."
fi

FIXTURE_SQL="
INSERT INTO companies (id, name, slug)
VALUES (101, 'WP006 Synthetic Company', 'wp006-synthetic-company');

INSERT INTO leads (
    id, company_id, name, phone, source, interest, status
)
VALUES (
    201, 101, 'WP006 Synthetic Lead', '11000000000',
    'wp006-test', 'backup-restore', 'new'
);

INSERT INTO customers (
    id, company_id, lead_id, name, phone, email
)
VALUES (
    301, 101, 201, 'WP006 Synthetic Customer',
    '11000000001', 'wp006@example.invalid'
);

INSERT INTO conversations (
    id, company_id, lead_id, customer_id, channel, status
)
VALUES (
    401, 101, NULL, 301, 'web', 'open'
);

INSERT INTO messages (
    id, conversation_id, sender_type, content
)
VALUES
    (
        501, 401, 'customer',
        'WP006 synthetic customer message'
    ),
    (
        502, 401, 'agent',
        'WP006 synthetic agent message'
    );
"

docker exec     -e PGPASSWORD="$DB_PASSWORD"     "$CONTAINER_NAME"     psql     -h 127.0.0.1     -U "$DB_ADMIN"     -d "$SOURCE_DB"     -v ON_ERROR_STOP=1     -c "$FIXTURE_SQL"     >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "Unable to insert the synthetic fixture."
fi

SOURCE_COUNTS="$(
    psql_value "$SOURCE_DB" "
        SELECT
            (SELECT COUNT(*) FROM companies),
            (SELECT COUNT(*) FROM leads),
            (SELECT COUNT(*) FROM customers),
            (SELECT COUNT(*) FROM conversations),
            (SELECT COUNT(*) FROM messages);
    "
)"
if [ "$?" -ne 0 ] || [ "$SOURCE_COUNTS" != "1|1|1|1|2" ]; then
    fail "Synthetic fixture counts are invalid before backup."
fi

# ---------------------------------------------------------------------------
# Logical backup to a temporary host file.
# ---------------------------------------------------------------------------

docker exec     -e PGPASSWORD="$DB_PASSWORD"     "$CONTAINER_NAME"     pg_dump     -h 127.0.0.1     -U "$DB_ADMIN"     -d "$SOURCE_DB"     -Fc     >"$BACKUP_FILE" 2>"$PGDUMP_ERR"
PGDUMP_EXIT=$?

if [ "$PGDUMP_EXIT" -ne 0 ]; then
    fail "pg_dump failed."
fi

if [ ! -s "$BACKUP_FILE" ]; then
    fail "Backup file was not created or is empty."
fi

echo "POSTGRES_BACKUP_CREATED_OK"

# ---------------------------------------------------------------------------
# Restore into a second empty database in the same container.
# ---------------------------------------------------------------------------

create_db "$RESTORE_DB"
if [ "$?" -ne 0 ]; then
    fail "Unable to create the restore database."
fi

docker exec     -i     -e PGPASSWORD="$DB_PASSWORD"     "$CONTAINER_NAME"     pg_restore     -h 127.0.0.1     -U "$DB_ADMIN"     -d "$RESTORE_DB"     <"$BACKUP_FILE" 2>"$PGRESTORE_ERR"
PGRESTORE_EXIT=$?

if [ "$PGRESTORE_EXIT" -ne 0 ]; then
    fail "pg_restore failed."
fi

echo "POSTGRES_RESTORE_OK"

# ---------------------------------------------------------------------------
# Post-restore verification.
# ---------------------------------------------------------------------------

RESTORE_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${HOST_PORT}/${RESTORE_DB}"

RESTORE_CURRENT="$(
    DATABASE_URL="$RESTORE_URL" uv run alembic current 2>&1
)"
RESTORE_CURRENT_EXIT=$?
if [ "$RESTORE_CURRENT_EXIT" -ne 0 ] ||
   ! printf '%s\n' "$RESTORE_CURRENT" | grep -q "$HEAD_REV"; then
    fail "Restored database is not at the expected Alembic head."
fi

RESTORED_COUNTS="$(
    psql_value "$RESTORE_DB" "
        SELECT
            (SELECT COUNT(*) FROM companies),
            (SELECT COUNT(*) FROM leads),
            (SELECT COUNT(*) FROM customers),
            (SELECT COUNT(*) FROM conversations),
            (SELECT COUNT(*) FROM messages);
    "
)"
if [ "$?" -ne 0 ] || [ "$RESTORED_COUNTS" != "1|1|1|1|2" ]; then
    fail "Restored row counts do not match the fixture."
fi

RELATIONSHIPS="$(
    psql_value "$RESTORE_DB" "
        SELECT
            l.company_id,
            c.company_id,
            v.company_id,
            c.lead_id,
            v.customer_id,
            COALESCE(v.lead_id::text, 'NULL')
        FROM leads l
        JOIN customers c ON c.id = 301
        JOIN conversations v ON v.id = 401
        WHERE l.id = 201;
    "
)"
if [ "$?" -ne 0 ] || [ "$RELATIONSHIPS" != "101|101|101|201|301|NULL" ]; then
    fail "Restored Company/Lead/Customer/Conversation relationships are invalid."
fi

COMPANY_DATA="$(
    psql_value "$RESTORE_DB" "
        SELECT id, name, slug
        FROM companies
        WHERE id = 101;
    "
)"
if [ "$?" -ne 0 ] ||
   [ "$COMPANY_DATA" != "101|WP006 Synthetic Company|wp006-synthetic-company" ]; then
    fail "Restored Company data differs from the synthetic fixture."
fi

LEAD_DATA="$(
    psql_value "$RESTORE_DB" "
        SELECT id, company_id, name, phone, source, interest, status
        FROM leads
        WHERE id = 201;
    "
)"
if [ "$?" -ne 0 ] ||
   [ "$LEAD_DATA" != "201|101|WP006 Synthetic Lead|11000000000|wp006-test|backup-restore|new" ]; then
    fail "Restored Lead data differs from the synthetic fixture."
fi

CUSTOMER_DATA="$(
    psql_value "$RESTORE_DB" "
        SELECT id, company_id, lead_id, name, phone, email
        FROM customers
        WHERE id = 301;
    "
)"
if [ "$?" -ne 0 ] ||
   [ "$CUSTOMER_DATA" != "301|101|201|WP006 Synthetic Customer|11000000001|wp006@example.invalid" ]; then
    fail "Restored Customer data differs from the synthetic fixture."
fi

CONVERSATION_DATA="$(
    psql_value "$RESTORE_DB" "
        SELECT
            id,
            company_id,
            COALESCE(lead_id::text, 'NULL'),
            customer_id,
            channel,
            status
        FROM conversations
        WHERE id = 401;
    "
)"
if [ "$?" -ne 0 ] ||
   [ "$CONVERSATION_DATA" != "401|101|NULL|301|web|open" ]; then
    fail "Restored Conversation data differs from the synthetic fixture."
fi

MESSAGE_DATA="$(
    psql_value "$RESTORE_DB" "
        SELECT
            id,
            conversation_id,
            sender_type,
            content
        FROM messages
        WHERE id IN (501, 502)
        ORDER BY id;
    "
)"
EXPECTED_MESSAGES="501|401|customer|WP006 synthetic customer message
502|401|agent|WP006 synthetic agent message"
if [ "$?" -ne 0 ] || [ "$MESSAGE_DATA" != "$EXPECTED_MESSAGES" ]; then
    fail "Restored Message data differs from the synthetic fixture."
fi

echo "POSTGRES_RESTORE_DATA_VERIFIED"
echo "BACKUP_RESTORE_VERIFIED"
