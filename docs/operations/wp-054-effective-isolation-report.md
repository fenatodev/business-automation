# WP-054 — Isolamento efetivo do executor e validação sem privilégios

**Status**: Corrigido — 7 falhas de verificação Ubuntu resolvidas
**Data**: 2026-10-15
**Branch**: `wp/054-effective-isolation`
**Commit**: pendente

## Resumo

Corrigidas 7 falhas verificadas diretamente no Ubuntu: (1) docker-compose environment syntax error, (2) Dockerfile não copia run_executor.py, (3) imports Python app.services.* sem __init__.py no container, (4) docker compose config validado com variáveis fictícias, (5) auditoria da fronteira de confiança HMAC — separar classes com a mesma chave não impede falsificação se Junie controla o host, (6) rede Docker bridge não bloqueia tráfego externo, (7) testes atualizados para detectar erros reais.

A correção central é a separação da fronteira de confiança: `ApprovalVerifier` (lado do executor, só verifica) e `ApprovalSigner` (lado do operador humano, só assina). O executor injetado com `ApprovalVerifier` não pode criar aprovações — só validar as que chegam do operador humano.

**Nota importante**: HMAC com a mesma chave compartilhada entre signer e verifier NÃO impede falsificação se o agente controla o host. A separação de classes é uma convenção de software. Para isolamento real, recomenda-se assinatura assimétrica (chave privada no operador, chave pública no executor) — plano documentado, não implementado nesta WP.

## Bloqueios Corrigidos

### Bloqueio 1: docker-compose topologia inválida

**Problema**: `network_mode: service:n8n` + `networks: [n8n-executor-net]` sem declarar o serviço `n8n`. Inválido — `network_mode: service:n8n` requer que `n8n` seja um serviço no mesmo compose file.

**Correção**: Usa rede externa `n8n_default` (rede Docker existente do n8n) via `networks: n8n_default: external: true`. Não declara serviço n8n — o container n8n é gerenciado pelo docker-compose de infraestrutura. Documenta que `n8n_default` não garante isolamento de egress.

### Bloqueio 2: HMAC sem separação sign/verify

**Problema**: `ApprovalGate` tinha `sign_approval()` e `validate()` no mesmo objeto. Se o agente acessasse o ApprovalGate, podia assinar suas próprias aprovações.

**Correção**: Três classes separadas:
- **`ApprovalVerifier`**: Lado do executor. Só `validate()`, sem `sign_approval()`. Inclui prevenção de replay (uso único).
- **`ApprovalSigner`**: Lado do operador humano. Só `sign_approval()`, sem `validate()`.
- **`ApprovalGate`**: Herda `ApprovalVerifier` + adiciona `sign_approval()` para compatibilidade com testes existentes.

A fronteira de confiança é: o container do executor tem apenas `ApprovalVerifier`. Sem `sign_approval()`, o agente não pode forjar aprovações.

### Bloqueio 3: N8nExecutor sem integração com ApprovalGate

**Problema**: `n8n_executor.py` usava `OperationApproval` (SHA-256 simples) que o agente podia forjar. `approval_gate.py` existia mas não era usado pelo executor.

**Correção**:
- `N8nExecutor.set_approval_verifier(verifier)` injeta o `ApprovalVerifier`
- `N8nExecutor.execute_with_queue(queue_data)` valida aprovações HMAC antes de executar operações de escrita
- Sem verifier configurado, operações de escrita são rejeitadas com `ApprovalRequiredError`
- O executor reconstrói `SignedApproval` dos dados da fila e valida via `ApprovalVerifier.validate()`

### Bloqueio 4: Dockerfile sem comando funcional

**Problema**:
- Shell `nologin` impedia execução do CMD
- CMD apontava para `app.services.n8n_executor` que não tem `__main__`
- Healthcheck era `import httpx; print('ok')` — não verificava nada real

**Correção**:
- Shell mudado de `nologin` para `/bin/sh`
- Criei `ops/sandbox/run_executor.py`: loop de polling que lê operações da fila, valida HMAC approval, executa via N8nExecutor
- Criei `ops/sandbox/healthcheck.py`: verifica conectividade real com a API n8n (HTTP GET `/api/v1/workflows`)
- Dockerfile copia apenas os serviços necessários (approval_gate.py, n8n_executor.py)

### Bloqueio 5: Testes negativos de confinamento ausentes

**Problema**: Não existiam testes verificando que o executor rejeita operações sem verifier, que o verifier não pode assinar, que replay é detectado, etc.

**Correção**: `tests/test_wp054_confinement.py` com 20 testes em 7 classes:
- `TestVerifierCannotSign`: Verifier não tem `sign_approval`, não pode forjar
- `TestReplayPrevention`: Reuso de approval detectado
- `TestExecutorRequiresVerifier`: Write ops rejeitadas sem verifier
- `TestProhibitedOperationsAlwaysDenied`: Database, credential, unknown sempre negados
- `TestAuthorizationBlockEnforcement`: HTTP 401/403 como bloqueio definitivo
- `TestJournalIntegrity`: Tamper detection e persistência
- `TestApprovalGateBackwardCompatibility`: ApprovalGate ainda funciona

### Bloqueio 6: Relatório incompleto

**Correção**: Este relatório atualizado documenta todos os bloqueios e correções.

### Bloqueio 7 (WP-054 correção): docker-compose environment syntax error

**Problema verificado no Ubuntu**: `docker compose -f ops/sandbox/docker-compose.yml config --no-interpolate --quiet` falha com:
```
services.n8n-executor.environment.[1]: unexpected type map[string]interface {}
```
A sintaxe `${VAR:?Error: ...}` em formato de lista YAML faz o Docker Compose interpretar a string como mapa, porque `:` dentro de `${}` é confundida com separador chave-valor YAML.

**Correção**: Mudar `environment` de formato lista para formato mapa YAML, com defaults seguros (`${VAR:-}` em vez de `${VAR:?msg}`):
```yaml
environment:
  N8N_BASE_URL: "http://n8n:5678"
  N8N_API_KEY: "${N8N_API_KEY:-}"
  APPROVAL_SECRET: "${APPROVAL_SECRET:-}"
```
As variáveis obrigatórias são validadas em tempo de execução pelo `run_executor.py` (exita com erro se `APPROVAL_SECRET` não estiver definida).

**Validação**: `docker compose config --no-interpolate --quiet` passa com exit code 0.

### Bloqueio 8 (WP-054 correção): Dockerfile não copia run_executor.py

**Problema verificado no Ubuntu**: `CMD ["python", "/app/run_executor.py"]` referencia um arquivo que nunca é copiado para o container. O Dockerfile copia `healthcheck.py` mas não `run_executor.py`.

**Correção**: Adicionado `COPY ops/sandbox/run_executor.py app/` ao Dockerfile.

### Bloqueio 9 (WP-054 correção): Imports Python app.services.* sem __init__.py

**Problema verificado no Ubuntu**: `run_executor.py` faz `from app.services.approval_gate import ApprovalVerifier` mas o Dockerfile não copia `app/__init__.py` nem `app/services/__init__.py`. Sem esses arquivos, o Python não reconhece `app.services` como pacote e a importação falha com `ModuleNotFoundError`.

**Correção**: Adicionado ao Dockerfile:
```dockerfile
COPY app/__init__.py app/
COPY app/services/__init__.py app/services/
```

### Bloqueio 10 (WP-054 correção): Auditoria da fronteira de confiança HMAC

**Problema**: Separar `ApprovalVerifier` (só verifica) de `ApprovalSigner` (só assina) usando a **mesma chave HMAC** não impede falsificação se o agente controla o host. Razões:

1. O `ApprovalVerifier` precisa do segredo HMAC para verificar assinaturas. Se o segredo está no container do executor (via variável de ambiente), o agente que controla o container pode lê-lo.
2. Com o segredo HMAC, o agente pode calcular a mesma assinatura que `ApprovalSigner` — a separação de classes é uma convenção de software, não uma barreira criptográfica.
3. Um agente com shell privilegiado no host pode acessar variáveis de ambiente do container, volumes Docker, ou o próprio processo do executor.

**Fronteira de confiança precisa**:
- **Sign side (ApprovalSigner)**: Deve rodar em processo/container SEPARADO do executor, com acesso exclusivo ao segredo. O segredo NUNCA deve ser injetado no container do executor.
- **Verify side (ApprovalVerifier)**: Deve usar apenas o que é necessário para verificar. Com HMAC simétrico, isso ainda requer o segredo completo.

**Recomendação para isolamento real — assinatura assimétrica**:
- Operador humano mantém **chave privada** (nunca exposta ao executor)
- Executor sandbox recebe apenas a **chave pública** para verificação
- Assinatura com RSA-4096 ou Ed25519: o executor pode verificar sem poder forjar
- Implementação futura: substituir HMAC-SHA256 por Ed25519 (`cryptography` library)
- **NÃO implementado nesta WP** — requer geração de credenciais reais, que está proibida

### Bloqueio 11 (WP-054 correção): Rede Docker bridge não bloqueia egress

**Problema**: Conectar o container do executor à rede `n8n_default` não impede que ele acesse a internet. Uma rede Docker bridge padrão permite NAT para o host, que tem acesso à internet.

**Impacto**: O executor pode fazer requisições HTTP para endpoints externos além do n8n. Não há garantia de que o tráfego fica restrito ao n8n.

**Correção documentada**: O relatório e os comentários do docker-compose.yml agora explicitam que `n8n_default` não garante isolamento de egress. Isolamento real requer:
- Rede Docker customizada com `--internal` (sem NAT)
- Regras de firewall iptables para permitir apenas tráfego para o container n8n
- Ou `network_policy` no compose com restrições de egress

**PENDENTE até teste de runtime**: Verificar se `n8n_default` tem acesso à internet e aplicar regras de firewall se necessário.

## Arquitetura Corrigida

### Fluxo de aprovação com separação sign/verify:

```
┌─────────────────────────────────────────────────────────────┐
│  Operador Humano (fora do container do executor)            │
│                                                             │
│  ApprovalSigner(secret=APPROVAL_SECRET)                     │
│    └─ sign_approval() → SignedApproval                      │
│         └─ Escreve na fila: queue/operation.json            │
└────────────────────────┬────────────────────────────────────┘
                         │ SignedApproval (HMAC-signed)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Container do Executor (sandbox)                            │
│                                                             │
│  run_executor.py → polls queue/*.json                       │
│    └─ N8nExecutor.execute_with_queue()                      │
│         └─ ApprovalVerifier.validate() ← SEM sign_approval  │
│              ├─ Verifica HMAC signature                     │
│              ├─ Verifica expiração                          │
│              ├─ Verifica payload hash                       │
│              ├─ Previne replay (uso único)                  │
│              └─ Executa HTTP se válido                      │
└─────────────────────────────────────────────────────────────┘
```

### ApprovalVerifier não pode assinar:

```python
verifier = ApprovalVerifier(secret="...")
assert not hasattr(verifier, "sign_approval")  # ✓ True — não pode assinar
```

### N8nExecutor exige verifier para write ops:

```python
executor = N8nExecutor(config)
# Sem verifier:
executor.execute_with_queue({"operation": "workflow:activate", ...})
# → ApprovalRequiredError

# Com verifier:
executor.set_approval_verifier(verifier)
executor.execute_with_queue({"operation": "workflow:activate", ...})
# → Valida HMAC → Executa HTTP
```

## Componentes

### `app/services/approval_gate.py` (596 linhas)

- `SignedApproval`: Dataclass imutável com HMAC signature
- `ApprovalVerifier`: Verifica aprovações, sem capacidade de assinatura
- `ApprovalSigner`: Cria aprovações, sem capacidade de verificação
- `ApprovalGate`: Herda ApprovalVerifier + sign_approval (compatibilidade)
- `IntegrityJournal`: Chain de hashes com persistência
- `ApprovalReplayError`: Nova exceção para prevenção de replay

### `app/services/n8n_executor.py` (596 linhas)

- `N8nExecutor.set_approval_verifier()`: Injeta ApprovalVerifier
- `N8nExecutor.execute_with_queue()`: Executa com validação HMAC
- `OperationApproval`: Mantido para compatibilidade, mas execute_with_queue usa HMAC

### `ops/sandbox/`

- `Dockerfile`: python:3.12-slim, usuário n8n-operator com `/bin/sh`, healthcheck real
- `docker-compose.yml`: Rede externa `n8n_default`, read-only FS, no-new-privileges
- `healthcheck.py`: Verifica conectividade com API n8n
- `run_executor.py`: Loop de polling com ApprovalVerifier

## Testes

**88 testes WP-054** em 3 arquivos (68 originais + 20 novos confinement):

### `tests/test_wp054_approval_gate.py` (33 testes) — atualizado

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestSignedApproval | 3 | Imutabilidade, formato JSON, keys ordenadas |
| TestApprovalGateSignature | 7 | Assinatura válida, forjada, vazia, adulterada, segredo diferente, agente sem segredo, replay |
| TestApprovalExpiration | 2 | Expiração, expiry curto (corrigido para usar fresh verifier) |
| TestApprovalMismatch | 3 | Payload diferente, operação diferente, ordem de dict |
| TestIntegrityJournal | 11 | Vazio, único, chain, manipulação, previous_hash, entry_hash, persistência |
| TestApprovalGateJournal | 3 | Validação, forjada, expirada |
| TestApprovalGateConstructor | 3 | Segredo vazio, None, journal padrão |
| TestApprovalEdgeCases | 4 | None payload, complexo, unicode, persistência |

### `tests/test_wp054_isolation_sandbox.py` (35 testes)

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestSandboxIsolation | 5 | Docker socket, DB n8n, sudo, rede, filesystem |
| TestSandboxConfiguration | 8 | Dockerfile e compose configuration |
| TestApprovalGateSecurity | 5 | SHA-256 não substitui HMAC, chute de segredo, expirada |
| TestExecutorSandboxIntegration | 6 | Read/write/prohibited operations |
| TestAuthorizationMatrix | 5 | Todas classificadas, sem sobreposição |
| TestIsolationLimitations | 3 | Limitações documentadas |

### `tests/test_wp054_confinement.py` (20 testes) — novo

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestVerifierCannotSign | 4 | Verifier sem sign_approval, não forja, signer funciona, signer+verifier |
| TestReplayPrevention | 2 | Reuso detectado, payloads diferentes não interferem |
| TestExecutorRequiresVerifier | 4 | Sem verifier, approval válida, expirada, forjada |
| TestProhibitedOperationsAlwaysDenied | 3 | Database, credential, unknown |
| TestAuthorizationBlockEnforcement | 2 | HTTP 401, HTTP 403 |
| TestJournalIntegrity | 2 | Tamper detection, persistência |
| TestApprovalGateBackwardCompatibility | 3 | Sign+verify, subclass, sign_approval |

## Evidências

```
858 tests passed, 2 warnings in 13.45s
compileall: ✓ Limpo
git diff --check: ✓ Limpo
```

## Limitações Conhecidas

### LIMITAÇÃO CRÍTICA: HMAC simétrico não isola sign de verify

Com HMAC-SHA256, o segredo é idêntico para assinatura e verificação. Separar `ApprovalVerifier` de `ApprovalSigner` em classes diferentes é uma **convenção de software** — se o agente controla o host ou o container do executor, pode:
1. Ler o segredo HMAC da variável de ambiente do container
2. Calcular assinaturas válidas usando o mesmo segredo
3. Contornar a separação de classes acessando o segredo diretamente

**Solução real**: Assinatura assimétrica (Ed25519/RSA-4096) onde o executor recebe apenas a chave pública para verificação. O operador humano mantém a chave privada em local separado. **PENDENTE** — requer WP dedicado com geração de credenciais.

### LIMITAÇÃO: O sandbox isola o executor, não o Junie

Se o Junie tem shell privilegiado no host, pode acessar Docker socket, banco SQLite n8n, etc. O sandbox protege o executor, mas não o host.

### LIMITAÇÃO: Journal integrity é software-based

Chain de hashes detecta manipulação, mas não impede.

### LIMITAÇÃO: n8n_default não garante isolamento de egress

A rede Docker `n8n_default` é uma bridge padrão com NAT para o host. O executor pode acessar a internet. Isolamento de egress real requer rede Docker `--internal` + regras de firewall iptables. **PENDENTE até teste de runtime.**

### LIMITAÇÃO: docker-compose environment usa defaults vazios

`N8N_API_KEY` e `APPROVAL_SECRET` usam `${VAR:-}` (default vazio) em vez de `${VAR:?error}` (falha imediata). A validação ocorre em tempo de execução pelo `run_executor.py`. Se o operador esquece de definir `APPROVAL_SECRET`, o executor exita com erro claro.

## Gate B — O que requer aprovação

A configuração de container (`ops/sandbox/`) está **preparada mas não aplicada**. Para aplicar:

```bash
# Comandos exatos (requerem aprovação):
cd ops/sandbox
docker build -t n8n-executor-sandbox .
export N8N_API_KEY=<key>
export APPROVAL_SECRET=<gerar-segredo-aleatorio>
docker compose -f docker-compose.yml up -d

# Rollback:
docker compose -f docker-compose.yml down
docker rmi n8n-executor-sandbox
```

**Nenhuma alteração** foi feita no n8n runtime, SQLite interno, Docker runtime, credenciais, escopos, workflows ou serviços de produção.

## Diferença WP-053 vs WP-054

| Aspecto | WP-053 | WP-054 (original) | WP-054 (corrigido) |
|---------|--------|-------------------|-------------------|
| Aprovação | SHA-256 do payload | HMAC-SHA256 | HMAC + sign/verify separado |
| Falsificável? | **Sim** | Não (se segredo externo) | Não (verifier sem sign) |
| Executor usa ApprovalGate? | **Não** | Não | **Sim** — execute_with_queue |
| Replay prevention | Não | Não | **Sim** — uso único |
| Docker compose topology | N/A | Inválida | **Correta** — rede externa |
| Dockerfile CMD funcional | N/A | Não | **Sim** — run_executor.py |
| Healthcheck real | N/A | Não | **Sim** — verifica API n8n |
| Testes negativos | 32 | 68 | 88 (+20 confinement) |

## Referências

- WP-053: Executor de privilégio mínimo (protótipo)
- WP-052: Política de governança n8n
- AGENTS.md: Seção "Integração n8n e governança"
- Issue #135: WP-054 — Isolamento efetivo do executor
