# WP-049 — Validação E2E Sintética n8n → FastAPI → Data Table

Status: **concluído com bloqueios documentados**.

## Resumo

Validação ponta a ponta da pipeline n8n → FastAPI privada → Data Table usando
evento 100% sintético. Testes de contrato (691) e teste de componente FastAPI
passaram. Execução E2E completa do workflow bloqueada por escopo de API key n8n.

## Evidências

### Preflight dos Serviços

| Serviço | Status | Detalhes |
|---------|--------|----------|
| n8n 2.40.7 | ✓ Rodando | Container `n8n`, rede `n8n_default`, IP 172.19.0.5 |
| PostgreSQL 17 | ✓ Rodando | Container `business-automation-dev-postgres-1` (healthy) |
| Data Table | ✓ Existente | `client0_commercial_review_queue` com 7 colunas corretas |
| Workflow | ✓ INACTIVE | `99999999-9999-4999-8999-999999999999`, placeholders intactos |
| FastAPI | ✓ Build OK | Imagem `ba-intake-private` construída com sucesso |

### Análise de Segurança do Workflow

- **7 nós lineares**: Webhook → Normalize → Dedupe → Rate Guard → FastAPI → Build Row → Data Table
- **Nenhum nó de envio externo** (WhatsApp, Telegram, email, etc.)
- **Nenhum nó de pagamento ou ação externa**
- **Webhook com Header Auth** e `responseMode: onReceived`
- **HTTP Request com timeout 10s**, redirects desabilitados
- **Build Row valida invariantes**: `can_send === false` e `simulation_only === true`

### Testes de Contrato

- **691 testes passando**, 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

### Teste de Componente FastAPI

Container `ba-intake-private` iniciado na rede `n8n_default` com:
- `BA_INTAKE_GENERATOR=static` (determinístico, sem rede)
- `BA_ACCESS_IDENTITIES_JSON` com token sintético
- `DATABASE_URL=sqlite:///:memory:` (sem banco real)

Resultado do endpoint `/internal/commercial-intake/evaluate`:
- **Status HTTP 200**
- Resposta com `can_send: false`, `simulation_only: true`
- `StaticCandidateGenerator` retornou pergunta de esclarecimento em português
- Container parado e removido após teste

### Credenciais n8n

- **2 credenciais de teste criadas** no n8n (BearerAuth + HeaderAuth)
- **Não foram removidas** — API key não tem escopo de exclusão
- Workflow restaurado para usar placeholders após teste

## Bloqueios para E2E Completo

### 1. Ativação do workflow via API — **Forbidden**

A API key n8n não tem escopo `workflow:activate`. O endpoint
`POST /api/v1/workflows/{id}/publish` retorna HTTP 403.

**Impacto**: Não é possível ativar o workflow via API para testar o webhook.
O webhook-test requer interação UI ("Execute workflow" no canvas).

**Alternativas**:
- Criar API key com escopo `workflow:activate` (requer aprovação)
- Ativar manualmente via UI para um único teste controlado

### 2. Inserção de linhas na Data Table via API — **Forbidden**

O endpoint `POST /api/v1/data-tables/{id}/rows` retorna HTTP 403.
A API key não tem permissão de escrita em Data Tables.

**Impacto**: Não é possível validar a gravação final da pipeline via API.

### 3. Credenciais de teste órfãs

Duas credenciais de teste (`business-automation-operator` BearerAuth e
`business-automation-internal-ingress` HeaderAuth) permanecem no n8n.
Remoção via API também retorna 403.

**Recomendação**: Remover manualmente via UI quando apropriado.

## Plano E2E Completo (quando autorizado)

1. Criar API key com escopos: `workflow:activate`, `data-table:write`
2. Ativar workflow via `POST /api/v1/workflows/{id}/publish`
3. Enviar POST sintético para webhook com Header Auth
4. Verificar linha na Data Table via `GET /api/v1/data-tables/{id}/rows`
5. Desativar workflow via `POST /api/v1/workflows/{id}/unpublish`
6. Remover credenciais de teste
7. Documentar resultados

## Rollback

- Workflow restaurado para placeholders: ✓
- Container FastAPI removido: ✓
- Imagem Docker `ba-intake-private` permanece local (inofensiva)
- Nenhum dado real foi usado
- Nenhuma mensagem foi enviada

## Conclusão

A pipeline n8n → FastAPI → Data Table está **validada nos níveis de contrato
e componente**. O teste E2E completo requer escopos adicionais na API key n8n
ou ativação manual via UI. Nenhum defeito de código foi encontrado.
