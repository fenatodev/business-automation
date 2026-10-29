# WP-058 — E2E Isolado do Motor n8n: Relatório de Execução

**Data:** 2026-10-29
**Branch:** `wp/058-commercial-pilot`
**Status:** E2E PASS com bloqueio documentado

## Resumo

Execução E2E completa do workflow n8n de 5 nós em ambiente Docker 100% isolado. Pipeline n8n → FastAPI → PostgreSQL validada ponta a ponta com dados sintéticos, sem depender da instância n8n principal.

## Ambiente Isolado

| Recurso | Configuração |
|---------|-------------|
| Rede Docker | `wp058-e2e` (isolada, removida após teste) |
| PostgreSQL | 17, volume temporário, migrations Alembic completas |
| n8n | 2.40.7, storage próprio, encryption key própria |
| FastAPI | `app.main:app`, rede isolada, alias `ba-intake-private` |
| Company seed | id=1, slug=wp058-e2e-test |

## Resultados

| Verificação | Resultado | Evidência |
|-------------|-----------|-----------|
| E2E N8N 5/5 | **PASS** | Execution ID 1, status=success, mode=webhook |
| Inbound Webhook | ✓ | Nó 1/5 executado |
| Normalize Safe Input | ✓ | Nó 2/5 executado |
| Persistent Event Dedupe | ✓ | Nó 3/5 executado |
| Coarse Rate Guard | ✓ | Nó 4/5 executado |
| Queue to Review (FastAPI) | ✓ | Nó 5/5 executado, HTTP 201 |
| FastAPI | **PASS** | `/review-queue/synthetic-trigger` → 201 |
| PostgreSQL | **PASS** | 2 linhas em `review_queue_items` |
| Idempotência | **PASS** | Mesmo event_id → item existente (id=2, created_at inalterado) |
| Painel /review-queue | **PASS** | `GET /review-queue/` listou itens corretamente |
| Limpeza | **PASS** | Containers, volumes, rede e imagem removidos |

## Evidência de Execução n8n

```
Execution ID: 1
Status: success
Mode: webhook
WaitForInput: false
Nodes executed: 5/5
  ✓ Inbound Webhook
  ✓ Normalize Safe Input
  ✓ Persistent Event Dedupe
  ✓ Coarse Rate Guard
  ✓ Queue to Review (FastAPI)
```

## Evidência de Persistência PostgreSQL

```sql
SELECT id, event_id, channel, status FROM review_queue_items;
```

| id | event_id | channel | status |
|----|----------|---------|--------|
| 1 | wp058-e2e-isolated-001 | whatsapp | pending |
| 2 | wp058-e2e-isolated-002 | whatsapp | pending |

## Evidência de Idempotência

POST com `event_id=wp058-e2e-isolated-002` (duplicado):
- Retornou item existente (id=2)
- `created_at` inalterado
- `count(*)` permaneceu 2 (sem duplicata)

## Testes de Contrato

- **1105 testes** passando, 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Bloqueio

**Remoção de workflows temporários na instância n8n principal:** BLOQUEADO

A API key `business-automation-integration` não possui escopo `workflow:delete`. HTTP 403 ao tentar remover:
- `d03b4f8a` — WP058 EPHEMERAL ENGINE PROBE - INACTIVE
- `1be7af9d` — Client0 - Commercial Intake Review (IMPORT COPY - INACTIVE)

Ambos permanecem INACTIVE. Remoção requer escopo ampliado via UI n8n ou API pública com aprovação humana.

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

A pipeline n8n → FastAPI → PostgreSQL foi validada ponta a ponta em ambiente 100% isolado. Os 5 nós do workflow executam corretamente, a autenticação Bearer funciona entre n8n e FastAPI, a persistência PostgreSQL é confirmada e a idempotência por event_id funciona. O único bloqueio restante é a remoção de workflows temporários na instância n8n principal, que requer escopo `workflow:delete` não disponível na API key atual.
