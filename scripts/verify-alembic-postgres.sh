#!/usr/bin/env bash
set -euo pipefail

container="business-automation-alembic-${RANDOM}-${RANDOM}"
container_id=""
password="temporary_alembic_validation_password"

cleanup() {
  if [[ -n "$container_id" ]]; then
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

container_id="$(docker run -d --rm \
  --name "$container" \
  -e POSTGRES_DB=alembic_validation \
  -e POSTGRES_USER=alembic_validation \
  -e POSTGRES_PASSWORD="$password" \
  -p 127.0.0.1::5432 \
  postgres:17)"

for _ in $(seq 1 30); do
  if docker exec "$container_id" pg_isready -U alembic_validation -d alembic_validation >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "$container_id" pg_isready -U alembic_validation -d alembic_validation >/dev/null
port="$(docker port "$container_id" 5432/tcp | head -n 1 | sed 's/.*://')"
database_url="postgresql+psycopg://alembic_validation:${password}@127.0.0.1:${port}/alembic_validation"

DATABASE_URL="$database_url" uv run alembic upgrade head
DATABASE_URL="$database_url" uv run alembic current
DATABASE_URL="$database_url" uv run alembic check

echo "Alembic fresh-install validation passed."
