# WP-058 — E2E Isolado do Motor n8n: Relatório Final

**Data:** 2026-10-29
**Branch:** `wp/058-commercial-pilot`
**Status:** E2E PASS — todas as validações concluídas

## Resumo

Execução E2E completa do workflow n8n de 5 nós em ambiente Docker 100% isolado. Pipeline n8n → FastAPI → PostgreSQL validada ponta a ponta com dados sintéticos. Workflow descartável `d03b4f8a` não encontrado na instância principal (já limpo em sessão anterior).

## Ambiente Isolado

| Recurso | Configuração |
|---------|-------------|
| Rede Docker | `wp058-e2e-net` (isolada, removida após teste) |
| PostgreSQL | 17-alpine, volume temporário, migrations Alembic completas |
| n8n | 2.40.7, storage próprio, encryption key própria, API key com full access |
| FastAPI | `app.main:app`, rede isolada, alias `wp058-e2e-fastapi` |
| Company seed | id=1, slug=wp058-e2e-test |

## Resultados

| Verificação | Resultado | Evidência |
|-------------|-----------|-----------|
| **E2E N8N 5/5** | **PASS** | Execution ID 1, status=success, mode=webhook |
| Inbound Webhook | ✓ | Nó 1/5 executado |
| Normalize Safe Input | ✓ | Nó 2/5 executado |
| Persistent Event Dedupe | ✓ | Nó 3/5 executado |
| Coarse Rate Guard | ✓ | Nó 4/5 executado |
| Queue to Review (FastAPI) | ✓ | Nó 5/5 executado, HTTP 200 |
| **FASTAPI** | **PASS** | POST `/review-queue/synthetic-trigger` → 201, GET `/review-queue/` → 200 |
| **POSTGRESQL** | **PASS** | 1 linha em `review_queue_items` |
| **IDEMPOTÊNCIA** | **PASS** | Mesmo event_id → 1 linha (sem duplicata) |
| **PAINEL** | **PASS** | `GET /review-queue/` listou item com intent, draft_reply e status |
| **LIMPEZA** | **PASS** | Containers, volumes e rede removidos |

## Evidência de Execução n8n

```
Execution ID: 1
Status: success
Mode: webhook
Workflow ID: 99999999-9999-4999-8999-999999999999
Nodes executed: 5/5
  ✓ Inbound Webhook
  ✓ Normalize Safe Input
  ✓ Persistent Event Dedupe
  ✓ Coarse Rate Guard
  ✓ Queue to Review (FastAPI)
Last node: Queue to Review (FastAPI)
```

## Evidência de Persistência PostgreSQL

```sql
SELECT id, event_id, channel, status, created_at FROM review_queue_items;
```

| id | event_id | channel | status |
|----|----------|---------|--------|
| 1 | wp058-e2e-001 | whatsapp | pending |

## Evidência de Idempotência

POST com `event_id=wp058-e2e-001` (duplicado):
- `count(*)` permaneceu **1** (sem duplicata)
- Item retornado por `GET /review-queue/` inalterado

## Workflow descartável d03b4f8a

**Não encontrado** na instância n8n principal. A instância possui zero workflows (banco SQLite vazio em `workflow_entity`). O workflow `WP058 EPHEMERAL ENGINE PROBE` foi criado em sessões anteriores de ambiente isolado e já foi removido com a limpeza dos recursos descartáveis.

## Testes de Contrato

- **1099 passed**, 6 failed (falhas pré-existentes por `.venv/bin/python` quebrado)
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Segurança

| Requisito | Status |
|-----------|--------|
| Zero dados reais de cliente | ✓ |
| Zero mensagens externas | ✓ |
| Ambiente isolado (não toca instância principal) | ✓ |
| Workflow desativado antes da limpeza | ✓ |
| Recursos temporários removidos | ✓ |
| Sem segredos expostos | ✓ |

## Conclusão

A pipeline n8n → FastAPI → PostgreSQL foi validada ponta a ponta em ambiente 100% isolado. Os 5 nós do workflow executam corretamente, a autenticação Bearer funciona entre n8n e FastAPI, a persistência PostgreSQL é confirmada e a idempotência por event_id funciona. Zero mudanças no código do repositório.
