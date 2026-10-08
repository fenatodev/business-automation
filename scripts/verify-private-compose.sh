#!/usr/bin/env bash
# WP-011: verify the canonical private PostgreSQL Compose configuration with
# synthetic credentials and an isolated Compose project.

set -u
set -o pipefail
umask 077

RUN_ID="$(date +%s)-$$"
PROJECT_NAME="business-automation-wp011-${RUN_ID}"
ENV_FILE="/tmp/business-automation-wp011-${RUN_ID}.env"
CONFIG_FILE="/tmp/business-automation-wp011-${RUN_ID}.compose.yml"

DB_NAME="wp011_db_${RUN_ID//-/_}"
DB_USER="wp011_user_${RUN_ID//-/_}"
DB_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
HOST_PORT=""
CONTAINER_ID=""
CLEANED=0

fail() {
    echo "ERROR: $1"
    exit 1
}

pick_loopback_port() {
    python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

cleanup() {
    if [ "$CLEANED" -eq 0 ]; then
        docker compose             -p "$PROJECT_NAME"             --env-file "$ENV_FILE"             down -v --remove-orphans             >/dev/null 2>&1 || true

        rm -f "$ENV_FILE" "$CONFIG_FILE" >/dev/null 2>&1 || true
        CLEANED=1
    fi
}

project_resources_remain() {
    local containers
    local volumes
    local networks

    containers="$(
        docker ps -a             --filter "label=com.docker.compose.project=$PROJECT_NAME"             -q 2>/dev/null
    )"
    volumes="$(
        docker volume ls             --filter "label=com.docker.compose.project=$PROJECT_NAME"             -q 2>/dev/null
    )"
    networks="$(
        docker network ls             --filter "label=com.docker.compose.project=$PROJECT_NAME"             -q 2>/dev/null
    )"

    [ -n "$containers" ] || [ -n "$volumes" ] || [ -n "$networks" ]
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "=== WP-011: private Compose validation ==="

command -v docker >/dev/null 2>&1 ||
    fail "Docker is unavailable."

command -v python3 >/dev/null 2>&1 ||
    fail "Python 3 is unavailable."

docker compose version >/dev/null 2>&1 ||
    fail "Docker Compose is unavailable."

if project_resources_remain; then
    fail "Resources already exist for this validation project."
fi

HOST_PORT="$(pick_loopback_port)"
if [ -z "$HOST_PORT" ] ||
   ! printf '%s' "$HOST_PORT" | grep -Eq '^[0-9]+$'; then
    fail "Unable to choose an isolated loopback port."
fi

cat >"$ENV_FILE" <<EOF
POSTGRES_PORT=$HOST_PORT
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASSWORD@127.0.0.1:$HOST_PORT/$DB_NAME
BA_ACCESS_IDENTITIES_JSON=[]
EOF
chmod 600 "$ENV_FILE"

docker compose     -p "$PROJECT_NAME"     --env-file "$ENV_FILE"     config     >"$CONFIG_FILE" 2>/dev/null
CONFIG_EXIT=$?

if [ "$CONFIG_EXIT" -ne 0 ]; then
    fail "docker compose config failed."
fi

if ! grep -Fq "127.0.0.1" "$CONFIG_FILE"; then
    fail "Rendered Compose config does not contain a loopback bind."
fi

if grep -Fq "0.0.0.0" "$CONFIG_FILE"; then
    fail "Rendered Compose config contains a wildcard IPv4 bind."
fi

echo "PRIVATE_COMPOSE_CONFIG_OK"

docker compose     -p "$PROJECT_NAME"     --env-file "$ENV_FILE"     up -d postgres     >/dev/null 2>&1
UP_EXIT=$?

if [ "$UP_EXIT" -ne 0 ]; then
    fail "Unable to start isolated PostgreSQL Compose service."
fi

CONTAINER_ID="$(
    docker compose         -p "$PROJECT_NAME"         --env-file "$ENV_FILE"         ps -q postgres 2>/dev/null
)"

if [ -z "$CONTAINER_ID" ]; then
    fail "Unable to resolve the isolated PostgreSQL container."
fi

WAITED=0
MAX_WAIT=60
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    docker exec         "$CONTAINER_ID"         pg_isready -U "$DB_USER" -d "$DB_NAME"         >/dev/null 2>&1
    if [ "$?" -eq 0 ]; then
        break
    fi

    sleep 1
    WAITED=$((WAITED + 1))
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    fail "PostgreSQL did not become ready."
fi

HOST_IP="$(
    docker inspect         --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostIp}}'         "$CONTAINER_ID" 2>/dev/null
)"
BOUND_PORT="$(
    docker inspect         --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}'         "$CONTAINER_ID" 2>/dev/null
)"

if [ "$HOST_IP" != "127.0.0.1" ]; then
    fail "PostgreSQL is not bound exclusively to IPv4 loopback."
fi

if [ "$BOUND_PORT" != "$HOST_PORT" ]; then
    fail "PostgreSQL host port differs from the synthetic validation port."
fi

PORT_BINDINGS="$(
    docker inspect         --format '{{json .NetworkSettings.Ports}}'         "$CONTAINER_ID" 2>/dev/null
)"

if printf '%s' "$PORT_BINDINGS" | grep -Eq '"HostIp":"(0\.0\.0\.0|::)"'; then
    fail "PostgreSQL has a wildcard port binding."
fi

echo "PRIVATE_COMPOSE_BIND_OK"

docker exec     "$CONTAINER_ID"     pg_isready -U "$DB_USER" -d "$DB_NAME"     >/dev/null 2>&1
if [ "$?" -ne 0 ]; then
    fail "PostgreSQL health verification failed."
fi

echo "PRIVATE_COMPOSE_POSTGRES_OK"

cleanup

if [ -e "$ENV_FILE" ] || [ -e "$CONFIG_FILE" ]; then
    fail "Temporary WP-011 files remain after cleanup."
fi

if project_resources_remain; then
    fail "WP-011 Compose resources remain after cleanup."
fi

echo "PRIVATE_COMPOSE_CLEANUP_OK"
echo "PRIVATE_COMPOSE_VERIFIED"
