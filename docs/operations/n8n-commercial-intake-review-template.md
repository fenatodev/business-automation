# Client0 — n8n commercial intake review (WP-058)

**Estado do arquivo Git:** template inativo, `active=false`; não é comprovação de deployment no n8n real.

Workflow: `ops/n8n/workflows/client0-commercial-intake-review.json`

## Fluxo versionado (5 nodes)

```text
Webhook (Header Auth)
 → Normalize Safe Input
 → Persistent Event Dedupe
 → Coarse Rate Guard
 → Queue to Review (FastAPI)
     POST http://ba-intake-private:8000/review-queue/synthetic-trigger
     Bearer operator (credencial local, não incluída no Git)
     → triagem + rascunho + review_queue_items em PostgreSQL
```

A fila atual é **PostgreSQL via FastAPI**; a Data Table interna do n8n **não participa mais deste template versionado**. A Data Table histórica ainda pode existir na instância n8n e não deve ser excluída automaticamente. O painel local `/operator` lê a fila via `GET /review-queue/` e registra decisões por `PATCH /review-queue/{id}/decision`. Aprovar um item **não dispara mensagem**.

## Contratos e limites conhecidos

- Webhook usa `headerAuth`; a requisição FastAPI usa `httpBearerAuth` com placeholders de credenciais no arquivo.
- `company_id` deriva da identidade Bearer do operador autenticado no FastAPI; não deve vir do corpo do webhook.
- A API utiliza `event_id` por tenant para idempotência persistente; o node Remove Duplicates limita também eventos repetidos antes da API, mas não substitui o índice único no PostgreSQL.
- O node Coarse Rate Guard usa dados estáticos do workflow e não é proteção transacional de rate limiting.
- O workflow não tem nós de envio externo, mas **não há evidência de execução n8n → FastAPI neste commit**.
- O endpoint `/review-queue/synthetic-trigger` é um endpoint de **piloto sintético**. Sem garantia de que todas as entradas recebidas sejam fictícias, não expor publicamente nem utilizar dados de clientes reais.
- A mudança do template não atualiza automaticamente o workflow existente na instância n8n. Confirmar revisão/importação e credenciais exclusivamente por APIs/UI suportadas; nunca manipular o banco interno do n8n.

## Validação já disponível

Testes Python cobrem o contrato JSON do workflow, autenticação declarada, endpoint FastAPI e fila. O script `scripts/demo_wp058_pipeline.py` validou, segundo o relatório do Junie, a persistência e decisões em PostgreSQL 17 descartável. **Isso não constitui prova de que a instância n8n importou ou executou esta versão.**

## Validação local restante — Junie

1. Sincronizar branch `wp/058-commercial-pilot` e executar testes do contrato e `node --check app/operator_ui/app.js`.
2. Validar o JSON do workflow com a versão instalada do n8n, sem ativar nem sobrescrever o workflow existente. Preferir importação isolada/temporária e remover apenas recursos de teste recém-criados.
3. Executar E2E n8n → API de teste → PostgreSQL descartável com payload sintético e credenciais **de teste**, se for possível sem alterar a stack operacional. Caso contrário, relatar bloqueio de integração. O teste de API/DB isolado já está coberto.
4. Registrar evidência sanitizada: código HTTP, row criada no banco de teste, duplicação, e ausência de execução de envio. Não anexar tokens nem PII.

**Não ativar produção nem enviar mensagens reais sem aprovação explícita.**
