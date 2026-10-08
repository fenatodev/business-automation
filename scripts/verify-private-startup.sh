#!/usr/bin/env bash
# WP-007: verify private startup, access revocation, and minimal logging
# using disposable local-only resources and synthetic credentials.

set -u
set -o pipefail

RUN_ID="$(date +%s)_$$"
CONTAINER_PREFIX="business-automation-startup-wp007-"
CONTAINER_NAME="${CONTAINER_PREFIX}${RUN_ID}"

DB_ADMIN="wp007_admin_${RUN_ID}"
DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
DB_NAME="wp007_db_${RUN_ID}"

ADMIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
OPERATOR_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
ADMIN_HASH="$(printf '%s' "$ADMIN_TOKEN" | sha256sum | awk '{print $1}')"
OPERATOR_HASH="$(printf '%s' "$OPERATOR_TOKEN" | sha256sum | awk '{print $1}')"

LOG1="/tmp/business-automation-wp007-${RUN_ID}-1.log"
LOG2="/tmp/business-automation-wp007-${RUN_ID}-2.log"

HOST_PORT=""
APP_PORT=""
API_PID=""
DB_URL=""

fail() {
    echo "ERROR: $1"
    exit 1
}

stop_api() {
    if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" 2>/dev/null; then
        kill "$API_PID" >/dev/null 2>&1 || true
        wait "$API_PID" 2>/dev/null || true
    fi
    API_PID=""
}

cleanup() {
    stop_api

    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi

    rm -f "$LOG1" "$LOG2" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

pick_loopback_port() {
    python3 - <<'PY'
import socket
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

http_status() {
    local url="$1"
    local token="${2:-}"

    TARGET_URL="$url" TOKEN_VALUE="$token" python3 - <<'PY'
import os
import urllib.error
import urllib.request

url = os.environ["TARGET_URL"]
token = os.environ.get("TOKEN_VALUE", "")

headers = {}
if token:
    headers["Authorization"] = "Bearer " + token

request = urllib.request.Request(url, headers=headers, method="GET")

try:
    with urllib.request.urlopen(request, timeout=3) as response:
        print(response.status)
except urllib.error.HTTPError as exc:
    print(exc.code)
except Exception:
    print("000")
PY
}

wait_for_health() {
    local port="$1"
    local attempts=0
    local code="000"

    while [ "$attempts" -lt 60 ]; do
        code="$(http_status "http://127.0.0.1:${port}/")"
        if [ "$code" = "200" ]; then
            return 0
        fi

        if [ -n "${API_PID:-}" ] && ! kill -0 "$API_PID" 2>/dev/null; then
            return 1
        fi

        sleep 0.5
        attempts=$((attempts + 1))
    done

    return 1
}

start_api() {
    local port="$1"
    local access_json="$2"
    local log_file="$3"

    DATABASE_URL="$DB_URL" \
    BA_ACCESS_IDENTITIES_JSON="$access_json" \
    uv run uvicorn app.main:app \
        --host 127.0.0.1 \
        --port "$port" \
        --log-level info \
        --no-use-colors \
        >"$log_file" 2>&1 &

    API_PID=$!
}

listener_is_private() {
    local port="$1"
    local sockets

    sockets="$(ss -ltn 2>/dev/null)"

    printf '%s\n' "$sockets" |
        grep -Eq "127\\.0\\.0\\.1:${port}[[:space:]]" || return 1

    printf '%s\n' "$sockets" |
        grep -Eq "0\\.0\\.0\\.0:${port}[[:space:]]" && return 1

    printf '%s\n' "$sockets" |
        grep -Eq "\[::\]:${port}[[:space:]]" && return 1

    return 0
}

wait_listener_gone() {
    local port="$1"
    local attempts=0

    while [ "$attempts" -lt 20 ]; do
        if ! ss -ltn 2>/dev/null |
            grep -Eq "127\\.0\\.0\\.1:${port}[[:space:]]"; then
            return 0
        fi

        sleep 0.25
        attempts=$((attempts + 1))
    done

    return 1
}

assert_logs_do_not_contain_secrets() {
    local secret

    for secret in \
        "$ADMIN_TOKEN" \
        "$OPERATOR_TOKEN" \
        "$ADMIN_HASH" \
        "$OPERATOR_HASH" \
        "$DB_PASSWORD" \
        "$DB_URL" \
        "$ACCESS_JSON_FULL" \
        "$ACCESS_JSON_REVOKED"
    do
        if [ -n "$secret" ] &&
           grep -Fq -- "$secret" "$LOG1" "$LOG2" 2>/dev/null; then
            fail "Captured logs contain a prohibited secret value."
        fi
    done
}

echo "=== WP-007: private startup and observability drill ==="

# ---------------------------------------------------------------------------
# Preflight.
# ---------------------------------------------------------------------------

for required in docker uv python3 sha256sum ss; do
    command -v "$required" >/dev/null 2>&1 ||
        fail "Required command is unavailable: $required"
done

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
    fail "Unable to determine Alembic head."
fi

EXISTING_WP007="$(
    docker ps -a --format '{{.Names}}' 2>/dev/null |
        grep "^$CONTAINER_PREFIX" || true
)"
if [ -n "$EXISTING_WP007" ]; then
    fail "A WP-007 container already exists; inspect it before a new run."
fi

# ---------------------------------------------------------------------------
# One disposable PostgreSQL 17 container, local-only.
# ---------------------------------------------------------------------------

docker run -d \
    --name "$CONTAINER_NAME" \
    --rm \
    -e POSTGRES_USER="$DB_ADMIN" \
    -e POSTGRES_PASSWORD="$DB_PASSWORD" \
    -e POSTGRES_DB="$DB_NAME" \
    -p 127.0.0.1::5432 \
    postgres:17 \
    >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "Unable to start disposable PostgreSQL."
fi

WAITED=0
while [ "$WAITED" -lt 60 ]; do
    docker exec "$CONTAINER_NAME" \
        pg_isready -U "$DB_ADMIN" -d "$DB_NAME" \
        >/dev/null 2>&1
    if [ "$?" -eq 0 ]; then
        break
    fi

    sleep 1
    WAITED=$((WAITED + 1))
done

if [ "$WAITED" -ge 60 ]; then
    echo "PostgreSQL did not become ready; recent container logs:"
    docker logs --tail 30 "$CONTAINER_NAME" 2>&1 || true
    fail "PostgreSQL readiness timed out."
fi

PORT_LINE="$(docker port "$CONTAINER_NAME" 5432/tcp 2>/dev/null | head -n 1)"
HOST_PORT="${PORT_LINE##*:}"
if [ -z "$HOST_PORT" ] || ! printf '%s' "$HOST_PORT" | grep -Eq '^[0-9]+$'; then
    fail "Unable to determine PostgreSQL host port."
fi

DB_URL="postgresql+psycopg://${DB_ADMIN}:${DB_PASSWORD}@127.0.0.1:${HOST_PORT}/${DB_NAME}"

MIGRATION_OUTPUT="$(
    DATABASE_URL="$DB_URL" uv run alembic upgrade head 2>&1
)"
MIGRATION_EXIT=$?
if [ "$MIGRATION_EXIT" -ne 0 ]; then
    fail "Alembic upgrade failed in the disposable database."
fi

CURRENT_OUTPUT="$(
    DATABASE_URL="$DB_URL" uv run alembic current 2>&1
)"
CURRENT_EXIT=$?
if [ "$CURRENT_EXIT" -ne 0 ] ||
   ! printf '%s\n' "$CURRENT_OUTPUT" | grep -q "$HEAD_REV"; then
    fail "Disposable database is not at the Alembic head."
fi

docker exec \
    -e PGPASSWORD="$DB_PASSWORD" \
    "$CONTAINER_NAME" \
    psql \
    -h 127.0.0.1 \
    -U "$DB_ADMIN" \
    -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -c "INSERT INTO companies (id, name, slug)
        VALUES (1, 'WP007 Synthetic Company', 'wp007-synthetic-company');" \
    >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "Unable to create the synthetic Company."
fi

ACCESS_JSON_FULL="$(
    ADMIN_HASH_VALUE="$ADMIN_HASH" \
    OPERATOR_HASH_VALUE="$OPERATOR_HASH" \
    python3 - <<'PY'
import json
import os

print(json.dumps([
    {
        "token_sha256": os.environ["ADMIN_HASH_VALUE"],
        "role": "admin",
    },
    {
        "token_sha256": os.environ["OPERATOR_HASH_VALUE"],
        "role": "operator",
        "company_id": 1,
    },
], separators=(",", ":")))
PY
)"

ACCESS_JSON_REVOKED="$(
    ADMIN_HASH_VALUE="$ADMIN_HASH" \
    python3 - <<'PY'
import json
import os

print(json.dumps([
    {
        "token_sha256": os.environ["ADMIN_HASH_VALUE"],
        "role": "admin",
    },
], separators=(",", ":")))
PY
)"

# ---------------------------------------------------------------------------
# Execution 1: private bind and authorized operator/admin behavior.
# ---------------------------------------------------------------------------

APP_PORT="$(pick_loopback_port)"
if [ -z "$APP_PORT" ]; then
    fail "Unable to select a loopback API port."
fi

start_api "$APP_PORT" "$ACCESS_JSON_FULL" "$LOG1"

if ! wait_for_health "$APP_PORT"; then
    fail "API did not become healthy during execution 1."
fi

if ! listener_is_private "$APP_PORT"; then
    fail "API listener is not restricted to 127.0.0.1."
fi

ROOT_CODE="$(http_status "http://127.0.0.1:${APP_PORT}/")"
UNAUTH_CODE="$(http_status "http://127.0.0.1:${APP_PORT}/leads")"
OPERATOR_LEADS_CODE="$(
    http_status "http://127.0.0.1:${APP_PORT}/leads" "$OPERATOR_TOKEN"
)"
OPERATOR_COMPANIES_CODE="$(
    http_status "http://127.0.0.1:${APP_PORT}/companies" "$OPERATOR_TOKEN"
)"
ADMIN_COMPANIES_CODE="$(
    http_status "http://127.0.0.1:${APP_PORT}/companies" "$ADMIN_TOKEN"
)"

if [ "$ROOT_CODE" != "200" ] ||
   [ "$UNAUTH_CODE" != "401" ] ||
   [ "$OPERATOR_LEADS_CODE" != "200" ] ||
   [ "$OPERATOR_COMPANIES_CODE" != "403" ] ||
   [ "$ADMIN_COMPANIES_CODE" != "200" ]; then
    fail "Execution 1 HTTP authorization checks failed."
fi

echo "PRIVATE_BIND_VERIFIED"
echo "PRIVATE_AUTH_VERIFIED"

FIRST_PORT="$APP_PORT"
stop_api

if ! wait_listener_gone "$FIRST_PORT"; then
    fail "Execution 1 listener remained after stopping the API."
fi

# ---------------------------------------------------------------------------
# Execution 2: same operator token after removal + restart must be revoked.
# ---------------------------------------------------------------------------

APP_PORT="$(pick_loopback_port)"
if [ -z "$APP_PORT" ]; then
    fail "Unable to select the second loopback API port."
fi

start_api "$APP_PORT" "$ACCESS_JSON_REVOKED" "$LOG2"

if ! wait_for_health "$APP_PORT"; then
    fail "API did not become healthy during execution 2."
fi

if ! listener_is_private "$APP_PORT"; then
    fail "Restarted API listener is not restricted to 127.0.0.1."
fi

REVOKED_CODE="$(
    http_status "http://127.0.0.1:${APP_PORT}/leads" "$OPERATOR_TOKEN"
)"
ADMIN_AFTER_RESTART_CODE="$(
    http_status "http://127.0.0.1:${APP_PORT}/companies" "$ADMIN_TOKEN"
)"

if [ "$REVOKED_CODE" != "401" ] ||
   [ "$ADMIN_AFTER_RESTART_CODE" != "200" ]; then
    fail "Access revocation checks failed after restart."
fi

echo "ACCESS_REVOCATION_VERIFIED"

SECOND_PORT="$APP_PORT"
stop_api

if ! wait_listener_gone "$SECOND_PORT"; then
    fail "Execution 2 listener remained after stopping the API."
fi

# ---------------------------------------------------------------------------
# Minimal logging and secret-leak checks.
# ---------------------------------------------------------------------------

grep -Fq "Uvicorn running on http://127.0.0.1:" "$LOG1" ||
    fail "Execution 1 startup log was not captured."

grep -Fq "GET / HTTP/" "$LOG1" ||
    fail "Health request was not present in execution 1 access logs."

grep -Fq "200 OK" "$LOG1" ||
    fail "A 200 response was not present in execution 1 logs."

grep -Fq "401 Unauthorized" "$LOG1" ||
    fail "A 401 response was not present in execution 1 logs."

grep -Fq "403 Forbidden" "$LOG1" ||
    fail "A 403 response was not present in execution 1 logs."

grep -Fq "401 Unauthorized" "$LOG2" ||
    fail "Revoked access was not visible as 401 in execution 2 logs."

assert_logs_do_not_contain_secrets

echo "MINIMAL_LOGGING_VERIFIED"
echo "PRIVATE_STARTUP_VERIFIED"
