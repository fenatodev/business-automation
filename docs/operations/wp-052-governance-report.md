# WP-052 — Governança de permissões, execução autônoma e fechamento pós-E2E

Status: **concluído com sucesso**.

## Resumo

Corrigida documentação e política de execução para proibir explicitamente
bypass de SQLite do n8n. Adicionados 22 testes de governança do executor.
Preparado procedimento seguro para credencial órfã `test-header` sem executar.

## Problema Crítico Resolvido

Os relatórios WP-050 e WP-051 recomendavam "escopos ampliados temporários
via banco SQLite do n8n". Esta prática foi **revogada**:

- **HTTP 403 é bloqueio definitivo** — não é autorização para contorná-lo
- **Nunca modificar o banco interno SQLite do n8n**
- **Nunca descriptografar ou extrair credenciais**
- **Nunca acessar chaves de criptografia internas**

## Changes

### 1. AGENTS.md — Nova seção "Integração n8n e governança"

Adicionada seção com 10 regras executáveis:

- Proibição explícita de modificar banco SQLite interno do n8n
- HTTP 401/403 como bloqueio definitivo sem contornamento
- Proibição de descriptografia de credenciais
- Proibição de acesso a chaves de criptografia
- Uso exclusivo de UI n8n ou API pública para gerenciar credenciais
- Documentação de limitação de testes estáticos
- Procedimento oficial para credenciais órfãs
- Workflow INACTIVE no repositório
- Ativação temporária com autorização explícita
- Sem envio externo sem aprovação

### 2. WP-050 — Errata datada

- Corrigida seção "Bloqueios Conhecidos": removida recomendação de SQLite bypass
- Adicionada seção "Errata WP-052 (2026-10-15)" revogando explicitamente
  a recomendação original de "escopos ampliados via banco SQLite"

### 3. WP-051 — Correções em duas seções

- **Riscos Identificados**: substituída recomendação de SQLite por
  "procedimento oficial (UI n8n ou API pública) com aprovação humana"
- **Bloqueios**: mesma correção — "Não usar banco SQLite interno do n8n"

### 4. Testes de governança do executor

Arquivo: `tests/test_wp052_executor_governance.py` — **22 testes** em 6 classes:

#### TestGovernancePolicyExists (7 testes)

- `test_governance_section_exists` — Seção existe no AGENTS.md
- `test_sqlite_bypass_is_prohibited` — Proibição explícita de SQLite
- `test_http_403_is_definitive_block` — 403 como bloqueio definitivo
- `test_credential_decryption_is_prohibited` — Sem descriptografia
- `test_encryption_key_access_is_prohibited` — Sem acesso a chaves
- `test_static_tests_limitation_is_documented` — Limitação documentada
- `test_orphan_credential_procedure_is_official` — Procedimento oficial

#### TestNoSQLiteBypassRecommendations (3 testes)

- `test_wp_report_has_errata_or_correction` — WP-050 e WP-051 corrigidos
- `test_agents_md_no_sqlite_bypass_recommendation` — AGENTS.md limpo

#### TestAuthorizationBlockEnforcement (5 testes)

- `test_workflow_uses_placeholders_not_real_creds` — Placeholders no JSON
- `test_workflow_is_inactive_in_repo` — Workflow INACTIVE
- `test_no_external_send_nodes_in_workflow` — Sem envio externo
- `test_webhook_requires_auth` — Autenticação obrigatória
- `test_fastapi_call_requires_bearer_auth` — Bearer Auth obrigatório

#### TestSecretMinimization (4 testes)

- `test_no_bearer_tokens_in_workflow` — Sem tokens hardcoded
- `test_no_api_keys_in_workflow` — Sem API keys hardcoded
- `test_no_real_credential_ids_in_workflow` — Sem IDs reais
- `test_no_env_files_in_tests` — Sem segredos em testes

#### TestOrphanCredentialProcedure (2 testes)

- `test_orphan_credential_is_documented` — Credencial órfã documentada
- `test_orphan_removal_requires_approval` — Aprovação necessária

### 5. Procedimento de credencial órfã

Arquivo: `docs/operations/orphan-credential-cleanup-procedure.md`

Procedimento preparado, **não executado**, com:

- Dois métodos: UI n8n (preferido) e API pública
- Pré-requisitos claros
- Passos detalhados
- Verificação pós-exclusão
- Proibições explícitas (SQLite, descriptografia, chaves)
- Rollback documentado
- Critérios de aprovação

## Plano de Pipeline Persistente

Para evoluir da demo sintética para pipeline persistente sem ativar
atendimento/comunicações:

1. **API key com escopos adequados** — Ampliar via UI n8n (não SQLite):
   - `workflow:activate` e `workflow:unpublish` para controle de workflow
   - `data-table:write` para gravação na Data Table
   - `credential:delete` para limpeza de credenciais órfãs

2. **Container FastAPI persistente** — Substituir container temporário
   por serviço versionado na rede `n8n_default`:
   ```bash
   docker run -d --name ba-intake-private \
     --network n8n_default \
     -p 8000:8000 \
     ba-api:latest
   ```

3. **Workflow com nome de container** — URL do FastAPI no workflow
   já usa `ba-intake-private` (não IP hardcoded).

4. **Monitoramento** — Adicionar verificação periódica via API:
   - Status do workflow (INACTIVE/ACTIVE)
   - Contagem de linhas na Data Table
   - Health check do FastAPI

5. **Sem comunicação externa** — Pipeline permanece com
   `can_send=false` e `simulation_only=true` até autorização explícita.

## Riscos

1. **Credencial test-header órfã** — Risco baixo, não referenciada.
   Procedimento preparado para remoção após aprovação.

2. **Testes estáticos não comprovam enforcement** — Os 22 testes validam
   documentação e estrutura, mas não garantem que o executor respeite
   as políticas em tempo real. Lacuna de enforcement marcada como PENDENTE.

3. **API key sem escopos de escrita** — Testes E2E futuros exigem
   escopos ampliados via UI n8n, não via SQLite.

## Bloqueios

1. **Remoção de credencial test-header** — Requer aprovação específica
   e acesso à UI n8n ou API key com escopo `credential:delete`.

2. **Testes E2E completos** — Requerem workflow ativo e API key com
   escopos ampliados via procedimento oficial.

3. **Enforcement no executor** — Testes estáticos validam documentação,
   mas não comprovam que o agente respeita HTTP 403 em tempo real.
   Solução requer instrumentação do executor (fora do escopo WP-052).

## Validação

- **738 testes** passando (717 existentes + 21 novos), 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Conclusão

A política de governança n8n está agora documentada em AGENTS.md com
regras executáveis claras. Os relatórios WP-050/051 foram corrigidos
para remover recomendações de bypass de SQLite. Os 22 testes de
governança validam que a documentação está completa e consistente.
O procedimento de credencial órfã está preparado para execução após
aprovação específica.

**Limitação conhecida**: Testes estáticos não comprovam enforcement
no executor. Esta lacuna deve ser marcada como PENDENTE até que
instrumentação do executor seja implementada.
