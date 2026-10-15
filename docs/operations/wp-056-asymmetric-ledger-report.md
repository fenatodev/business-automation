# WP-056 — Fail-closed obrigatório, consumo atômico e assinatura assimétrica

**Status**: CONCLUÍDO
**Branch**: `wp/056-assymmetric-ledger`
**Testes**: 925 passando (37 novos)

## Implementado

### 1. Assinatura assimétrica Ed25519

- **`Ed25519Signer`**: Segredo privado exclusivo do aprovador humano. Gera `SignedApprovalEd25519` com nonce único.
- **`Ed25519Verifier`**: Chave pública apenas. Verifica assinatura, expiração, payload hash e consome no ledger. Não possui método `sign`.
- **`SignedApprovalEd25519`**: Approval com nonce, payload hash, operator, expiração e assinatura Ed25519 hex-encoded.

### 2. Ledger atômico SQLite (ApprovalLedger)

- Banco SQLite **novo e isolado** — nunca o banco interno do n8n.
- Tabela `consumed_approvals` com `UNIQUE` em `approval_id`.
- WAL mode + `PRAGMA synchronous=FULL` + fsync após cada write.
- Fail-closed: se o ledger é ilegível, corrompido ou inacessível, a operação falha com `LedgerError`.
- Teste de concorrência real entre processos: dois processos tentando consumir o mesmo nonce — um succeeds, outro detecta replay via `IntegrityError`.

### 3. Eliminação completa do bypass SHA-256 legado

- `N8nExecutor.execute()`: `OperationApproval` (SHA-256) é **sempre rejeitado** em todos os caminhos.
- Sem verifier configurado: operações de escrita são **negadas** — nunca aceitam `OperationApproval`.
- Com verifier configurado: apenas `signed_approval` criptográfico é aceito.

### 4. Fail-closed em todos os caminhos

- Sem verifier → `ApprovalRequiredError`
- Sem ledger disponível → `LedgerError`
- Ledger corrompido → `LedgerError` na inicialização
- HTTP 401/403 → `AuthorizationBlockError` sem retry

## Testes (37 novos)

| Classe | Contagem | Cobertura |
|--------|----------|-----------|
| `TestEd25519AsymmetricSignatures` | 10 | Sign/verify, trust boundary, tampering, expiração, nonce |
| `TestAtomicSQLiteLedger` | 9 | UNIQUE constraint, WAL, persistência, corrupção, fail-closed |
| `TestCrossProcessConcurrency` | 2 | Concorrência real entre processos, consumo sequencial |
| `TestEd25519VerifierWithLedger` | 5 | Integração verifier+ledger, replay após restart, sem ledger |
| `TestN8nExecutorWithEd25519` | 4 | Executor com Ed25519, sem verifier, legacy rejection |
| `TestFailClosed` | 5 | Sem verifier, ledger corrompido, 401/403 |
| `TestOperationValidation` | 1 | Operation mismatch |

## Testes corrigidos

- **WP-055**: `test_legacy_approval_works_without_verifier` → `test_legacy_approval_rejected_without_verifier` (agora espera `ApprovalRequiredError`)
- **WP-053**: 5 testes atualizados para esperar `ApprovalRequiredError` ao usar `OperationApproval` legado

## Limitações

1. **Junie tem shell privilegiado no host**: Se o agente controla o host, pode acessar chaves, ledger e contornar o executor. O isolamento real requer container dedicado sem Docker socket.
2. **Ed25519 não é enforced pelo executor**: O executor aceita qualquer verifier com método `validate`. A integração Ed25519 é via `set_approval_verifier()`.
3. **Chaves sintéticas em testes**: Chaves Ed25519 são geradas por fixture — não há credenciais reais.
4. **Consumo antes de HTTP**: O consumo no ledger ocorre após a validação da assinatura, mas antes do HTTP externo. Se o HTTP falha, a aprovação já foi consumida — reconciliação GET seria necessária para retry.

## Bloqueios

- Nenhum bloqueio pendente.
- Assinatura assimétrica Ed25519 implementada e testada.
- Ledger atômico com concorrência real validada.
- Bypass SHA-256 eliminado em todos os caminhos.
