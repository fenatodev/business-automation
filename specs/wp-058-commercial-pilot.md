# WP-058 — Piloto comercial autônomo com dados sintéticos e LGPD

## Objetivo

Entregar automação comercial funcional: pipeline sintético reproduzível de
entrada → triagem → rascunho → fila de revisão → decisão do operador → estado final,
com idempotência, tratamento de falhas, evidências de execução e LGPD.

## Contexto

- n8n workflow `client0-commercial-intake-review.json` já validado (INACTIVE).
- FastAPI possui routers de opportunities, leads, conversations, commercial-intake evaluate.
- Intake evaluate endpoint (`/internal/commercial-intake/evaluate`) retorna `IntakeDecision`.
- Data Table n8n: `client0_commercial_review_queue` com schema: event_id, status, intent, draft_reply, needs_human_review, flags_json, received_at.
- Stack: Python 3.12, FastAPI, SQLAlchemy, SQLite (testes), PostgreSQL (prod).

## Entregáveis

### 1. Review Queue API (novo router)

Endpoints para o operador gerenciar a fila de revisão:

- `GET /review-queue` — lista itens pendentes (tenant-isolated)
- `GET /review-queue/{item_id}` — detalha um item
- `PATCH /review-queue/{item_id}/decision` — aprova ou rejeita com nota do operador
- `POST /review-queue/synthetic-trigger` — dispara um evento sintético completo (dev/test only)

### 2. Commercial Pipeline Service

`app/services/commercial_pipeline.py` — orquestra o fluxo completo:

1. **Intake**: recebe evento (channel, message, event_id), valida e deduplica por event_id.
2. **Triage**: chama intake evaluate (static ou ollama) para classificar intent.
3. **Draft**: gera rascunho de resposta baseado na decisão.
4. **Queue**: persiste na review queue com status=pending.
5. **Decision**: operador aprova/rejeita via API.
6. **Finalize**: atualiza status final e registra evidência.

### 3. Modelos de dados

Novo modelo `ReviewQueueItem`:

- id, company_id (FK), event_id (unique), channel, message, intent,
  draft_reply, status (pending/approved/rejected), operator_note,
  needs_human_review, flags_json, created_at, updated_at

### 4. Testes E2E sintéticos

- `tests/test_commercial_pipeline_e2e.py` — fluxo completo com dados sintéticos.
- Idempotência: mesmo event_id não cria duplicata.
- Falha do agente: mensagem preservada, HTTP 503.
- Cross-tenant isolation: operador company A não vê dados company B.
- Decisão de operador: approve/reject altera status corretamente.

### 5. LGPD

- Dados sintéticos apenas — nenhum dado real de cliente.
- Minimização: apenas campos necessários para o piloto.
- Segregação por tenant via company_id.
- Sem PII em logs.

## Regras

- Workflow n8n permanece INACTIVE.
- Sem comunicação externa real.
- Sem dados reais de clientes.
- Sem bypass de 401/403.
- Sem modificação do banco interno do n8n.

## Definição de pronto

- `uv run pytest` passa com todos os novos testes.
- `.venv/bin/python -m compileall app tests` passa.
- `git diff --check` passa.
- Pipeline sintético completo executável via endpoint dedicado.
- Fila de revisão funcional com approve/reject.
- Idempotência verificada por teste.
- Branch pushada, PR aberto, sem merge automático.
