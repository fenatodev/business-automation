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
existing_database_url="postgresql+psycopg://alembic_validation:${password}@127.0.0.1:${port}/alembic_existing_validation"
invalid_database_url="postgresql+psycopg://alembic_validation:${password}@127.0.0.1:${port}/alembic_invalid_validation"
owner_constraint_previous_revision="963028cb1f76"
previous_revision="c14b8f9d2e3a"
head_revision="e8f2a9c1d5b7"

run_alembic() {
  DATABASE_URL="$1" uv run alembic "${@:2}"
}

run_owner_validation() {
  DATABASE_URL="$1" uv run python scripts/verify-conversation-owner-constraint.py "${@:2}"
}

run_agent_config_validation() {
  DATABASE_URL="$1" uv run python scripts/verify-company-agent-config.py "${@:2}"
}

run_alembic "$database_url" upgrade head
run_alembic "$database_url" current | grep -F "${head_revision} (head)"
run_alembic "$database_url" check
run_owner_validation "$database_url" seed --channel fresh-validation
run_owner_validation "$database_url" verify --channel fresh-validation
run_agent_config_validation "$database_url" verify

docker exec "$container_id" createdb -U alembic_validation alembic_existing_validation
run_alembic "$existing_database_url" upgrade "$previous_revision"
run_owner_validation "$existing_database_url" seed --channel existing-validation
run_alembic "$existing_database_url" upgrade head
run_owner_validation "$existing_database_url" verify --channel existing-validation
run_agent_config_validation "$existing_database_url" verify
run_alembic "$existing_database_url" downgrade -1
run_agent_config_validation "$existing_database_url" assert-absent
run_owner_validation "$existing_database_url" verify --channel existing-validation
run_alembic "$existing_database_url" upgrade head
run_owner_validation "$existing_database_url" verify --channel existing-validation
run_agent_config_validation "$existing_database_url" verify

docker exec "$container_id" createdb -U alembic_validation alembic_invalid_validation
run_alembic "$invalid_database_url" upgrade "$owner_constraint_previous_revision"
run_owner_validation "$invalid_database_url" seed-invalid
if run_alembic "$invalid_database_url" upgrade head; then
  echo "Expected upgrade with an invalid conversation owner to fail." >&2
  exit 1
fi
run_alembic "$invalid_database_url" current | grep -F "${owner_constraint_previous_revision}"

echo "Alembic fresh, existing-install, and invalid-data validation passed."
