#!/usr/bin/env bash
# WP-003: Harness PostgreSQL descartável para caracterizar Alembic
# Não usa set -e para controle explícito de falhas

set -o pipefail

CONTAINER_NAME="business-automation-alembic-wp003-$(date +%s)"
PORT=""
FAILED_REASON=""
EXPECTED_FAILURE=false

# Gera identificadores/credencial únicos para este teste
RUN_ID="$(date +%s)_$"
DB_USER="alembic_test_user_${RUN_ID}"
DB_NAME="alembic_test_db_${RUN_ID}"
DB_PASSWORD="alembic_test_pass_${RUN_ID}"

cleanup() {
    if [ -n "$CONTAINER_NAME" ] && docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT INT TERM

# Verifica disponibilidade de Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker não disponível"
    exit 1
fi

# Cria container PostgreSQL temporário
# O usuário e banco são criados após o container estar pronto
docker run -d \
    --name "$CONTAINER_NAME" \
    --rm \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -p 0:5432 \
    postgres:17

# Aguarda pg_isready
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec "$CONTAINER_NAME" pg_isready -U postgres >/dev/null 2>&1; then
        break
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: PostgreSQL não iniciou em tempo"
    exit 1
fi

# Cria usuário e banco dentro do container
docker exec "$CONTAINER_NAME" psql -U postgres -c "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';" >/dev/null 2>&1
docker exec "$CONTAINER_NAME" psql -U postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";" >/dev/null 2>&1

# Extrai porta do container
PORT=$(docker port "$CONTAINER_NAME" 5432 | cut -d: -f2)
if [ -z "$PORT" ]; then
    echo "ERROR: Não foi possível obter porta do container"
    exit 1
fi

# Constrói DATABASE_URL exclusivamente do container
DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${PORT}/${DB_NAME}"

# Executa alembic upgrade head com DATABASE_URL como variável de ambiente
echo "Executando: alembic upgrade head contra PostgreSQL descartável em 127.0.0.1:${PORT}"
echo "----------------------------------------"

# Passa DATABASE_URL apenas para este processo; não imprime a credencial.
OUTPUT=$(DATABASE_URL="$DATABASE_URL" uv run alembic upgrade head 2>&1)
EXIT_CODE=$?

echo "----------------------------------------"
echo "Saída do Alembic:"
echo "$OUTPUT"
echo "----------------------------------------"

if [ $EXIT_CODE -eq 0 ]; then
    FAILED_REASON="Alembic completou inesperadamente (exit 0)"
    exit 1
fi

# Verifica se a falha é relacionada a leads/UndefinedTable
if echo "$OUTPUT" | grep -qi "leads\|UndefinedTable\|relation.*leads.*does not exist"; then
    EXPECTED_FAILURE=true
    FAILED_REASON="Falha esperada: tabela leads não existe"
else
    FAILED_REASON="Falha não esperada: $(echo "$OUTPUT" | head -5)"
    exit 1
fi

echo ""
echo "EXPECTED_ALEMBIC_FAILURE_CONFIRMED"
exit 0
