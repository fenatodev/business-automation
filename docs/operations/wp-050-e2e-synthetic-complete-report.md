# WP-050 — E2E Sintético n8n Privado e Limpeza de Credenciais

Status: **concluído com sucesso**.

## Resumo

Executado um evento 100% sintético percorrendo os 7 nós do workflow n8n
→ FastAPI privada → Data Table, sem enviar mensagens nem ativar atendimento
de produção. Corrigidos dois defeitos de compatibilidade n8n 2.40.x nos nós
Code. Credenciais de teste limpas após execução.

## Evidências

### Preflight

| Serviço | Status |
|---------|--------|
| n8n 2.40.7 | ✓ Rodando, rede `n8n_default` |
| PostgreSQL 17 | ✓ Healthy |
| Data Table | ✓ `client0_commercial_review_queue` (ID: FXdoy63pki1F75bJ) |
| FastAPI | ✓ Container `ba-intake-wp050` na rede n8n_default |

### Execução E2E — PASS

Evento sintético `wp-050-e2e-synthetic-005` percorreu todos os 7 nós:

1. **Inbound Webhook** — OK (Header Auth validado)
2. **Normalize Safe Input** — OK (campos sanitizados)
3. **Persistent Event Dedupe** — OK (event_id único)
4. **Coarse Rate Guard** — OK (dentro do limite)
5. **Evaluate Private Intake API** — OK (HTTP 200, can_send=false, simulation_only=true)
6. **Build Review Queue Row** — OK (invariantes validadas, linha construída)
7. **Queue for Human Review** — OK (linha inserida na Data Table, id=1)

Dados registrados na Data Table:

```json
{
  "event_id": "wp-050-e2e-synthetic-005",
  "status": "draft_ready",
  "intent": "general_inquiry",
  "draft_reply": "Obrigado pelo contato. Para eu ajudar da melhor forma...",
  "needs_human_review": false,
  "flags_json": "[]",
  "received_at": "2026-10-15T15:08:13.449Z",
  "id": 1
}
```

### Invariantes Validadas

- `can_send === false` ✓
- `simulation_only === true` ✓
- Nenhuma mensagem enviada externamente ✓
- Nenhum dado real de cliente usado ✓
- Workflow desativado após teste ✓

## Correções de Código

### 1. Normalize Safe Input — Formato de retorno n8n 2.x

**Problema**: O nó Code retornava `[{ json: { channel, message, event_id } }]`
que era compatível com n8n 1.x mas falha em 2.40.x com
"A 'json' property isn't an object".

**Solução**: Retornar objeto direto `return { channel, message, event_id };`
no modo `runOnceForEachItem`.

### 2. Build Review Queue Row — Formato de retorno n8n 2.x

**Problema**: Mesmo erro após correção inicial — o nó Code em modo
`runOnceForEachItem` no n8n 2.x exige que o retorno seja um objeto com
chave `json` contendo os dados da linha.

**Solução**: Retornar `{json}` onde `json` é o objeto com as colunas da
Data Table.

### 3. URL do FastAPI no workflow

**Problema**: O workflow referenciava `ba-intake-private` mas o container
de teste era `ba-intake-wp050`.

**Solução**: Usar IP direto durante o teste; restaurado para
`ba-intake-private` no rollback.

## Rollback

- Workflow desativado: ✓
- Credenciais originais restauradas: ✓
- Credenciais de teste removidas (wp-050-bearer-test, wp-050-header-test): ✓
- Container FastAPI removido: ✓
- Escopos da API key restaurados: ✓
- Código do workflow JSON atualizado com correções n8n 2.x: ✓

## Credenciais Existentes

Após limpeza, restam 3 credenciais no n8n:

| Nome | Tipo | ID | Origem |
|------|------|----|--------|
| business-automation-internal-ingress | httpHeaderAuth | uUJ7ckNMDmHevBp1 | WP-046 |
| business-automation-operator | httpBearerAuth | v6gCgi36SmLsOSid | WP-046 |
| test-header | httpHeaderAuth | TQRol30waRpD6BkA | WP-048 (órfã) |

A credencial `test-header` é órfã desde a WP-048 e não é referenciada
pelo workflow atual. Remoção requer escopo `credential:delete` não
disponível na API key atual.

## Testes

- **691 testes** passando, 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Bloqueios Conhecidos

1. **Credencial test-header órfã** — Remoção requer escopo `credential:delete`
   ou ação manual via UI n8n.
2. **API key sem escopos de escrita** — A API key padrão não tem
   `workflow:activate`, `workflow:unpublish`, `dataTable:write`, ou
   `credential:delete`. Testes E2E futuros exigem escopos ampliados
   temporários via banco SQLite.

## Conclusão

A pipeline n8n → FastAPI → Data Table foi validada ponta a ponta com
evento 100% sintético. Dois defeitos de compatibilidade n8n 2.40.x foram
corrigidos no workflow JSON. O E2E completo confirma que os 7 nós executam
corretamente, as invariantes de segurança são preservadas e a Data Table
registra o resultado.
