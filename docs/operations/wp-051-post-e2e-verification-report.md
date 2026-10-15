# WP-051 — Verificação Pós-E2E: Estado, Drift e Segurança

Status: **concluído com sucesso**.

## Resumo

Verificado o estado real dos serviços n8n após o WP-050 E2E sintético:
workflow INACTIVE, escopos da API key restritos, containers limpos, sem
mudanças persistentes inesperadas. Adicionados 26 testes de segurança para
impedir bypass de autorização e drift na importação de workflows.

## Evidências de Estado Real

### Workflow n8n

| Propriedade | Valor |
|-------------|-------|
| Nome | Client0 - Commercial Intake Review (INACTIVE) |
| Ativo | **False** ✓ |
| Versão | a5b1bdd8-6a10-417e-b0c3-d20e1e388b33 |
| Nós | 7 (Webhook → Normalize → Dedupe → Rate Guard → FastAPI → Build Row → Data Table) |

Verificado via API n8n (`GET /api/v1/workflows/99999999-...`).

### API Key — Escopos Restritos

| Operação | HTTP Status | Esperado |
|----------|-------------|----------|
| GET /workflows | 200 | 200 ✓ |
| GET /credentials | 200 | 200 ✓ |
| GET /data-tables | 200 | 200 ✓ |
| POST /workflows/{id}/publish | **403** | 403 ✓ |
| DELETE /credentials/{id} | **403** | 403 ✓ |

A API key `business-automation-integration` possui apenas escopos de leitura
e atualização de workflow. Escopos de ativação, desativação e exclusão de
credenciais foram removidos após o WP-050.

### Containers de Teste

Nenhum container `ba-intake-*` encontrado. Container `ba-intake-wp050`
removido após WP-050.

### Credenciais n8n

| Nome | Tipo | ID | Status |
|------|------|----|--------|
| business-automation-internal-ingress | httpHeaderAuth | uUJ7ckNMDmHevBp1 | Em uso (WP-046) |
| business-automation-operator | httpBearerAuth | v6gCgi36SmLsOSid | Em uso (WP-046) |
| test-header | httpHeaderAuth | TQRol30waRpD6BkA | **Órfã** (WP-048) |

A credencial `test-header` não é referenciada pelo workflow atual.
Remoção bloqueada por falta de escopo `credential:delete` na API key.

## Análise de Drift

### Workflow JSON (repositório) vs n8n (runtime)

| Aspecto | Status |
|---------|--------|
| Nome do workflow | ✓ Sincronizado |
| Código dos nós Code | ✓ Sincronizado |
| Conexões | ✓ Sincronizadas |
| Credenciais do webhook | ✗ **Drift esperado** — repo usa `REPLACE_LOCAL_HEADER_CREDENTIAL_ID`, n8n usa `uUJ7ckNMDmHevBp1` |
| Credenciais do FastAPI | ✗ **Drift esperado** — repo usa `REPLACE_LOCAL_BEARER_CREDENTIAL_ID`, n8n usa `v6gCgi36SmLsOSid` |

O drift de credenciais é **comportamento correto**: o repositório armazena
placeholders para que o workflow possa ser importado em ambientes diferentes
sem expor IDs de credenciais reais.

### Referências da credencial test-header

A credencial `test-header` (ID: TQRol30waRpD6BkA) foi criada durante WP-048
e não é referenciada por nenhum workflow ativo. É uma credencial órfã que
persiste no n8n por falta de permissão para remoção via API.

## Testes de Segurança Adicionados

Arquivo: `tests/test_wp051_post_e2e_security.py` — **26 testes** em 4 classes:

### TestCredentialDriftDetection (5 testes)

- `test_workflow_uses_header_credential_placeholder` — Webhook usa placeholder
- `test_workflow_uses_bearer_credential_placeholder` — FastAPI usa placeholder
- `test_no_real_n8n_credential_ids_in_workflow_json` — Nenhum ID real de WP-044 a WP-050 no JSON
- `test_credential_ids_are_placeholders_not_names` — IDs são placeholders (nomes são metadados seguros)
- `test_no_hardcoded_auth_values_in_workflow` — Sem tokens ou chaves hardcoded

### TestPostE2EState (5 testes)

- `test_workflow_is_inactive` — Workflow marcado como inativo
- `test_workflow_name_indicates_inactive` — Nome contém "INACTIVE"
- `test_normalize_node_uses_n8n_2x_compatible_return` — Formato n8n 2.x
- `test_build_row_node_uses_n8n_2x_compatible_return` — Formato n8n 2.x
- `test_fastapi_url_uses_container_name_not_ip` — URL usa nome de container

### TestSecurityInvariants (9 testes)

- `test_no_external_send_nodes` — Sem nós de envio externo
- `test_webhook_requires_authentication` — Header Auth obrigatório
- `test_webhook_is_post_only` — Apenas POST
- `test_fastapi_call_requires_bearer_auth` — Bearer Auth obrigatório
- `test_fastapi_call_does_not_follow_redirects` — Redirecmentos desabilitados
- `test_build_row_validates_can_send_invariant` — can_send=false validado
- `test_build_row_validates_simulation_only_invariant` — simulation_only=true validado
- `test_dedupe_is_by_event_id` — Deduplicação por event_id
- `test_rate_limiting_is_present` — Rate limiting presente

### TestAuthorizationBypassPrevention (7 testes)

- `test_workflow_id_is_uuid4` — ID válido UUID4
- `test_no_script_injection_in_node_names` — Sem injeção de script
- `test_code_nodes_use_javascript_language` — JavaScript explícito
- `test_data_table_uses_named_reference` — Referência nomeada, não ID hardcoded
- `test_workflow_has_no_unexpected_connections` — Conexões lineares esperadas
- `test_no_active_on_failure_connections` — Sem conexões de falha ativas
- `test_http_request_has_timeout` — Timeout configurado

## Riscos Identificados

1. **Credencial test-header órfã** — Persiste no n8n sem ser referenciada.
   Risco baixo: não é usada por nenhum workflow. Remoção requer ação manual
   via UI n8n ou escopo `credential:delete` temporário.

2. **API key sem escopos de escrita** — Testes E2E futuros exigem escopos
   ampliados temporários via banco SQLite. Procedimento documentado no WP-050.

3. **Drift de credenciais esperado** — O workflow JSON no repositório usa
   placeholders enquanto o n8n runtime usa IDs reais. Isso é intencional e
   seguro, mas requer atenção durante importação.

## Bloqueios

1. **Remoção de credencial test-header** — Requer escopo `credential:delete`
   não disponível na API key atual. Ação manual via UI n8n necessária.

2. **Testes E2E futuros** — Requerem escopos ampliados temporários da API key
   via modificação direta do banco SQLite do n8n.

## Validação

- **717 testes** passando (691 existentes + 26 novos), 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Conclusão

O estado pós-WP-050 está limpo e seguro: workflow INACTIVE, escopos restritos,
sem containers órfãos, sem credenciais reais no repositório. Os 26 testes de
segurança adicionados previnem que drift de credenciais ou bypass de autorização
ocorram em importações futuras do workflow.
