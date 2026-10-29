# WP-055 — Eliminar bypass legado e persistir aprovações após reinício

**Status**: Concluído
**Data**: 2026-10-15
**Branch**: `wp/055-durable-approvals`
**Commit**: pendente

## Resumo

Corrigidos 2 dos 5 riscos identificados no issue #136:

1. **Consumo durável de aprovações**: `ApprovalVerifier._used_approvals` agora é persistido no journal file. Após restart, o verifier carrega as aprovações já consumidas, impedindo replay.
2. **Bypass do caminho legado SHA-256**: `N8nExecutor.execute()` agora aceita `signed_approval` (HMAC) como parâmetro preferido. Se o verifier estiver configurado, aprovações legado `OperationApproval` são rejeitadas.

## Riscos Resolvidos

### Risco 1: `_used_approvals` em memória permite replay após restart

**Problema**: `ApprovalVerifier._used_approvals` era um `set[str]` em memória. Se o processo do executor reiniciava, o set era limpo e uma aprovação já usada podia ser replayada.

**Solução**:
- `ApprovalVerifier.__init__()` agora chama `_load_used_approvals()` para carregar aprovações já consumidas do journal file.
- `ApprovalVerifier.validate()` persiste o ID da aprovação consumida no journal com status `approval_consumed`.
- Ao reiniciar, o novo `ApprovalVerifier` carrega esses IDs do journal e rejeita replay.

**Limitação**: A durabilidade depende do journal ter um `path` definido. Sem path, o comportamento volta a ser volátil.

### Risco 2: `N8nExecutor.execute()` caminho legado SHA-256 forjável

**Problema**: `N8nExecutor.execute()` aceitava `OperationApproval` com hash SHA-256 simples. O agente podia calcular o hash do payload e criar uma aprovação falsa, pois SHA-256 não requer segredo.

**Solução**:
- `execute()` agora aceita `signed_approval` (SignedApproval com HMAC) como parâmetro preferido.
- Se `signed_approval` for fornecido, o `ApprovalVerifier` valida a assinatura HMAC.
- Se apenas `approval` (legado) for fornecido e o verifier estiver configurado, a operação é rejeitada com `ApprovalRequiredError`.
- O caminho legado só funciona quando **nenhum** verifier está configurado, com um warning de depreciação.

## Riscos PENDENTES

### Risco 3: `APPROVAL_SECRET` como variável de ambiente

**Status**: PENDENTE. O `run_executor.py` aceita `APPROVAL_SECRET` como variável de ambiente. Se o agente controla o container do executor, pode ler o segredo e gerar HMAC válidos.

**Solução recomendada**: Assinatura assimétrica (Ed25519/RSA) onde o executor recebe apenas a chave pública para verificação. O operador humano mantém a chave privada em local separado.

### Risco 4: `IntegrityJournal` hash-chain não autentica histórico

**Status**: PENDENTE. Se o agente pode reescrever o journal file, a chain de hashes pode ser manipulada retroativamente.

**Solução recomendada**: Separar armazenamento do journal do executor, ou assinar cada entrada com chave privada do operador.

### Risco 5: Docker Compose usa `n8n_default` sem egress zero

**Status**: PENDENTE. O sandbox do executor conectado à rede `n8n_default` pode acessar a internet.

**Solução recomendada**: Usar `--network none` para testes e rede `--internal` + firewall rules para produção.

## Testes

19 novos testes em `tests/test_wp055_durable_approvals.py`:

- **TestDurableApprovalConsumption** (3): replay após restart bloqueado, aprovação diferente funciona, sem journal path = sem durabilidade
- **TestLegacyBypassBlocked** (4): legado rejeitado com verifier, HMAC funciona, legado funciona sem verifier, sem aprovação = rejeitado
- **TestTamperedSignature** (3): payload modificado rejeitado, assinatura adulterada rejeitada, segredo errado rejeitado
- **TestAuthorizationBlocks** (3): 401 bloqueia, 403 bloqueia, sem retry em 403
- **TestUnauthorizedCalls** (3): operação proibida bloqueada, acesso direto ao banco bloqueado, leitura sem aprovação funciona
- **TestExpiredApproval** (1): aprovação expirada rejeitada
- **TestExecutorWithSignedApproval** (2): execute() com signed_approval funciona, sem verifier = rejeitado

## Evidências

- **888 testes** passando (869 existentes + 19 novos), 0 falhas
- `compileall`: ✓ Limpo
- `git diff --check`: ✓ Limpo

## Limitações Conhecidas

1. **HMAC simétrico não isola sign de verify**: Se o agente controla o host ou o container do executor, pode ler o segredo HMAC e forjar assinaturas. Assinatura assimétrica é necessária para isolamento real.
2. **Journal pode ser reescrito**: Se o agente tem acesso ao journal file, pode manipular a chain de hashes.
3. **Isolamento do Junie no host continua PENDENTE**: O executor é protegido, mas o Junie com shell privilegiado no host pode contornar.

## Referências

- Issue #136: https://github.com/fenatodev/business-automation/issues/136
- WP-053: `app/services/n8n_executor.py` (executor de privilégio mínimo)
- WP-054: `app/services/approval_gate.py` (ApprovalVerifier/Signer)
