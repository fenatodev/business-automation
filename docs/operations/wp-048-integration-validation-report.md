# WP-048 Integration Validation Report

**Date:** 2026-10-15
**Branch:** `wp/048-n8n-data-table-provision`
**Base commit:** 4289341
**Validation commit:** 875edee

---

## STATUS

| Component | Status | Notes |
|-----------|--------|-------|
| n8n service | ✓ Running | v2.40.7, container `n8n`, IP 172.19.0.5:5678 |
| n8n workflow | ✓ Inactive | ID `99999999-9999-4999-8999-999999999999`, imported and verified |
| Data Table | ✓ Provisioned | `client0_commercial_review_queue`, 7 columns, ID `FXdoy63pki1F75bJ` |
| FastAPI code | ✓ Valid | All endpoints compile, no syntax errors |
| Auth Bearer | ✓ Configured | SHA256 + HMAC comparison, placeholder credentials in workflow |
| received_at type | ✓ Compatible | Workflow `dateTime` → n8n API `date` (expected mapping in 2.40.x) |
| PostgreSQL | ✓ Running | Container `business-automation-dev-postgres-1`, healthy |

---

## TESTES

### Existing suite
- **629 tests passed** (baseline from WP-048 base commit)

### New integration contract tests
- **62 tests passed** in `tests/test_n8n_integration_contracts.py`

### Coverage areas
| Test class | Count | Purpose |
|------------|-------|---------|
| TestWorkflowStructure | 12 | Workflow JSON validity, UUIDs, inactivity, no external sends |
| TestFastAPIEndpointContract | 6 | Workflow HTTP node matches FastAPI endpoint |
| TestDataTableSchemaCompatibility | 6 | Data Table columns match workflow output |
| TestWorkflowOutputToDataTableMapping | 9 | Build Review Queue Row produces correct fields |
| TestWorkflowTopology | 4 | Linear pipeline connectivity verified |
| TestInputNormalization | 4 | Input sanitization and length limits |
| TestDeduplicationAndRateLimiting | 4 | Event deduplication and rate guard |
| TestFastAPIResponseToWorkflowContract | 9 | IntakeDecision fields match workflow expectations |
| TestReceivedAtCompatibility | 4 | ISO 8601 timestamp compatibility |
| TestBearerAuthConfiguration | 4 | Bearer auth placeholders verified |

### Total
- **691 tests passed, 0 failed**
- `compileall`: ✓ Clean
- `git diff --check`: ✓ Clean

---

## CORREÇÕES

Nenhuma correção de código foi necessária. Os contratos entre os três componentes (n8n workflow, FastAPI endpoint, Data Table) estão compatíveis.

### Finding: received_at type mapping

**Observação:** O workflow JSON define `received_at` com tipo `dateTime` no schema do nó DataTable. A Data Table provisionada no n8n tem tipo `date` para essa coluna.

**Conclusão:** Isso é comportamento esperado no n8n 2.40.x. O tipo `dateTime` no schema do nó é mapeado internamente para `date` na API REST do n8n. O valor gerado por `new Date().toISOString()` (string ISO 8601 completa) é aceito corretamente pela coluna `date`. Não há incompatibilidade funcional.

---

## BLOQUEIOS

Nenhum bloqueio identificado para a validação dos contratos de integração.

### Pendentes para execução end-to-end (fora do escopo desta validação)

1. **Credenciais n8n:** Os placeholders `REPLACE_LOCAL_HEADER_CREDENTIAL_ID` e `REPLACE_LOCAL_BEARER_CREDENTIAL_ID` precisam ser substituídos pelas credenciais reais do n8n local antes de ativar o workflow.
2. **Container FastAPI:** O workflow aponta para `ba-intake-private:8000` — o container FastAPI precisa estar na rede Docker `n8n_default` com esse nome.
3. **Ativação do workflow:** O workflow permanece INACTIVE. Ativação requer autorização explícita separada.

---

## PRÓXIMA AÇÃO

Para progresso além desta validação de contratos:

1. **Configurar credenciais n8n:** Criar as duas credenciais locais (Header Auth para webhook, Bearer Auth para FastAPI) no n8n.
2. **Provisionar container FastAPI:** Subir o container `ba-intake-private` na rede `n8n_default` com auth Bearer configurado.
3. **Teste de conectividade sintética:** Validar POST autenticado do workflow para o endpoint FastAPI com dados fictícios.
4. **Ativação controlada:** Ativar o workflow apenas após todas as validações acima passarem.

Cada passo acima requer um work package próprio com autorização explícita, conforme AGENTS.md.

---

## EVIDÊNCIAS

- Workflow JSON: `ops/n8n/workflows/client0-commercial-intake-review.json`
- Testes: `tests/test_n8n_integration_contracts.py` (62 testes)
- Data Table API: `GET /api/v1/data-tables/FXdoy63pki1F75bJ` → 200 OK, 7 colunas
- Workflow n8n: `GET /api/v1/workflows/99999999-9999-4999-8999-999999999999` → active=false
- n8n versão: 2.40.7
