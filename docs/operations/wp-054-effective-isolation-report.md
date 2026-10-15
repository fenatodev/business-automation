# WP-054 — Isolamento efetivo do executor e validação sem privilégios

**Status**: Implementado — Fase A completa, Gate B preparado  
**Data**: 2026-10-15  
**Branch**: `wp/054-effective-isolation`  
**Commit**: pendente

## Resumo

Transformei o protótipo da WP-053 em um sistema de aprovação com integridade verificável. O defeito fundamental da WP-053 — o agente podia falsificar aprovações calculando seu próprio SHA-256 — foi corrigido com HMAC-SHA256. Adicionei journal com chain de hashes para detecção de manipulação retroativa. Preparei configuração de container restrito (Dockerfile + compose) sem aplicar mudanças no host.

## Problema da WP-053

A `OperationApproval` da WP-053 usava SHA-256 do payload como vínculo de aprovação. O agente podia:

1. Calcular `hashlib.sha256(payload).hexdigest()` livremente
2. Criar `OperationApproval(content_hash=hash_calculado, ...)`
3. O executor validava o hash — que o próprio agente tinha calculado

**SHA-256 do payload não autentica quem autorizou.** Qualquer processo com acesso ao payload pode calcular o hash.

## Implementado

### 1. ApprovalGate com HMAC-SHA256 (`app/services/approval_gate.py`)

O `ApprovalGate` resolve o defeito da WP-053 usando HMAC-SHA256:

- **Segredo HMAC externo**: O segredo `APPROVAL_SECRET` deve vir de fora do processo do agente (variável de ambiente do container, vault, etc.)
- **Assinatura cobre todos os campos**: operation, payload_hash, operator, expires_at — nenhum campo pode ser alterado após a assinatura
- **Verificação com `hmac.compare_digest`**: Timing-attack safe
- **Expiração obrigatória**: Aprovações expiram após janela configurável (padrão 5 minutos)

Fluxo correto:
```python
# Humano operador (com acesso ao segredo):
approval = gate.sign_approval(
    operation="workflow:activate",
    payload={"workflow_id": "..."},
    operator="human-admin"
)

# Executor valida antes de executar:
gate.validate(approval, payload)  # Levanta ApprovalSignatureError se falsificado
```

### 2. IntegrityJournal com chain de hashes

O `IntegrityJournal` substitui a lista simples da WP-053:

- **Chain de hashes**: Cada entrada inclui o hash da entrada anterior
- **Detecção de manipulação**: `verify_integrity()` detecta se qualquer entrada foi alterada
- **Persistência**: Journal pode ser salvo em arquivo JSON e verificado após reload
- **Arquivo corrompido**: Inicia limpo em vez de crashar

### 3. Container restrito preparado (`ops/sandbox/`)

Configuração preparada mas **NÃO aplicada** (Gate B):

**Dockerfile**:
- Base `python:3.12-slim`
- Usuário `n8n-operator` sem shell (`nologin`)
- Sem sudo, sem curl, sem ferramentas privilegiadas
- Apenas `httpx` como dependência

**docker-compose.yml**:
- `read_only: true` — filesystem read-only
- `no-new-privileges:true` — impede elevação de privilégio
- Sem mount do Docker socket
- Sem mount do filesystem n8n
- Sem `network_mode: host`
- tmpfs para `/tmp` com `noexec,nosuid`
- Resource limits: 0.5 CPU, 256MB RAM
- `APPROVAL_SECRET` injetado via variável de ambiente

### 4. Matriz de autorização

Todas as 16 operações `OperationType` estão classificadas em exatamente uma categoria:

| Categoria | Operações | Comportamento |
|-----------|-----------|---------------|
| READ_ONLY (7) | workflow:get/list/status, credential:list/metadata, data-table:read, execution:list | Sem aprovação |
| APPROVAL_REQUIRED (4) | workflow:update, data-table:write, workflow:activate/deactivate | HMAC approval obrigatória |
| PROHIBITED (5) | credential:delete/read_secret, database:direct/modify, workflow:publish | Sempre bloqueadas |

## Testes

**68 novos testes** em 2 arquivos:

### `tests/test_wp054_approval_gate.py` (33 testes)

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestSignedApproval | 3 | Imutabilidade, formato JSON, keys ordenadas |
| TestApprovalGateSignature | 7 | Assinatura válida, forjada, vazia, adulterada, segredo diferente, agente sem segredo, replay |
| TestApprovalExpiration | 2 | Expiração, expiry curto |
| TestApprovalMismatch | 3 | Payload diferente, operação diferente, ordem de dict |
| TestIntegrityJournal | 11 | Vazio, único, chain, manipulação, previous_hash, entry_hash, persistência, arquivo adulterado, corrompido, primeiro entry, chain |
| TestApprovalGateJournal | 3 | Validação, forjada, expirada |
| TestApprovalGateConstructor | 3 | Segredo vazio, None, journal padrão |
| TestApprovalEdgeCases | 4 | None payload, complexo, unicode, persistência |

### `tests/test_wp054_isolation_sandbox.py` (35 testes)

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestSandboxIsolation | 5 | Docker socket, DB n8n, sudo, rede, filesystem |
| TestSandboxConfiguration | 8 | Dockerfile (sem socket, sem root, sem sudo), compose (sem socket, sem n8n data, read-only, no-new-privileges, sem host network) |
| TestApprovalGateSecurity | 5 | SHA-256 não substitui HMAC, chute de segredo, expirada, journal tamper, operação diferente |
| TestExecutorSandboxIntegration | 6 | Read sem approval, write com approval, proibidas, database, credenciais, publish |
| TestAuthorizationMatrix | 5 | Todas classificadas, sem sobreposição, listas esperadas |
| TestIsolationLimitations | 3 | Segredo externo, journal software-only, Junie não isolado |

## Evidências

```
838 tests passed, 2 warnings in 12.99s
compileall: ✓ Limpo
git diff --check: ✓ Limpo
```

## Limitações Conhecidas

### LIMITAÇÃO CRÍTICA: O ApprovalGate é seguro APENAS se o segredo estiver fora do alcance do agente

Se o agente Junie tem acesso ao segredo HMAC (por exemplo, lendo `/proc/<pid>/environ` do container, ou acessando o mesmo `.env`), o ApprovalGate não impede bypass. A segurança depende de:

1. **Container separado**: O executor roda em container diferente do Junie
2. **Segredo injetado apenas no container do executor**: Via Docker secrets ou variável de ambiente não visível fora do container
3. **Nenhum compartilhamento de filesystem**: Junie não pode ler o journal ou o segredo

### LIMITAÇÃO: O sandbox isola o executor, não o Junie

Se o Junie tem shell privilegiado no host:
- Pode acessar Docker socket diretamente
- Pode ler banco SQLite n8n diretamente
- Pode executar `docker exec` no container do executor

O sandbox protege o executor, mas não protege o host do Junie. Isolamento completo do Junie requer:
1. Junie em container próprio sem Docker socket
2. Comunicação executor↔Junie apenas via API
3. Network policy restritiva

### LIMITAÇÃO: Journal integrity é software-based

A chain de hashes detecta manipulação, mas não impede. Um atacante com write access pode modificar o journal — a verificação vai falhar, mas a modificação já ocorreu. Proteção real exigiria hardware (TPM, secure enclave).

## Gate B — O que requer aprovação

A configuração de container (`ops/sandbox/Dockerfile` + `docker-compose.yml`) está **preparada mas não aplicada**. Para aplicar:

```bash
# Comandos exatos (requerem aprovação):
cd ops/sandbox
docker build -t n8n-executor-sandbox .
export N8N_API_KEY=<key>
export APPROVAL_SECRET=<gerar-segredo-aleatorio>
docker-compose up -d

# Rollback:
docker-compose down
docker rmi n8n-executor-sandbox
```

**Riscos**:
- Container novo compete por recursos com containers existentes
- `APPROVAL_SECRET` precisa ser gerado e armazenado de forma segura
- Network do executor precisa ser configurada para alcançar n8n

**Nenhuma alteração** foi feita no n8n runtime, SQLite interno, Docker runtime, credenciais, escopos, workflows ou serviços de produção.

## Diferença WP-053 vs WP-054

| Aspecto | WP-053 | WP-054 |
|---------|--------|--------|
| Aprovação | SHA-256 do payload | HMAC-SHA256 com segredo externo |
| Falsificável pelo agente? | **Sim** | **Não** (se segredo for externo) |
| Journal | Lista simples | Chain de hashes com integridade |
| Detecção de manipulação | Não | Sim |
| Container restrito | Plano documentado | Dockerfile + compose prontos |
| Testes de enforcement | 32 | 68 |

## Referências

- WP-053: Executor de privilégio mínimo (protótipo)
- WP-052: Política de governança n8n
- AGENTS.md: Seção "Integração n8n e governança"
- Issue #135: WP-054 — Isolamento efetivo do executor
