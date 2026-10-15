# WP-053 — Enforcement Real para Executor Autônomo n8n

**Status**: Implementado com limitações documentadas
**Data**: 2026-10-15
**Branch**: `wp/053-minimal-privilege-executor`
**Commit**: pendente

## Resumo

Implementado um executor de privilégio mínimo (`app/services/n8n_executor.py`) que fornece enforcement REAL da política de governança n8n em tempo de execução. Diferente dos testes estáticos da WP-052, este executor valida cada operação contra uma allowlist antes de executar, bloqueando operações proibidas e exigindo aprovação explícita para operações de escrita.

## Inventário de Privilégios

### Acesso atual do agente ao host

O inventário revelou que o agente Junie tem acesso irrestrito ao host:

| Recurso | Acesso | Risco |
|---------|--------|-------|
| Docker socket (`/var/run/docker.sock`) | ✓ Grupo `docker` | Crítico — controle total de containers |
| Banco SQLite n8n (`/mnt/infra/apps/n8n/data/database.sqlite`) | ✓ Via Python `sqlite3` | Crítico — leitura/escrita direta |
| CLI Docker | ✓ Comando disponível | Crítico — exec em containers |
| Sudo | ✓ Grupo `sudo` (requer senha) | Alto — elevação de privilégio |
| Filesystem n8n | ✓ Mount bind visível | Médio — leitura de dados |

### Pontos de bypass identificados

1. **Docker exec**: `docker exec n8n <comando>` permite executar qualquer comando dentro do container n8n
2. **SQLite direto**: `python3 -c "import sqlite3; ..."` permite ler/modificar o banco n8n
3. **Docker socket**: acesso ao socket permite criar containers com mounts arbitrários
4. **Filesystem host**: o mount bind `/mnt/infra/apps/n8n/data` é acessível diretamente

### Conclusão do inventário

**Sem confinamento real de container/usuário, um agente com shell irrestrito pode contornar qualquer wrapper Python.** O executor implementado fornece uma barreira de software, mas não impede que o agente acontorne usando o acesso direto ao host.

## Implementação

### Executor de privilégio mínimo

`app/services/n8n_executor.py` implementa:

1. **Classificação de operações**:
   - `READ_ONLY_OPERATIONS`: leitura sem aprovação
   - `APPROVAL_REQUIRED_OPERATIONS`: escrita com aprovação vinculada a hash
   - `PROHIBITED_OPERATIONS`: sempre bloqueadas (database, credenciais, publish)

2. **Aprovação vinculada a conteúdo**:
   - Cada aprovação contém um hash SHA-256 do payload exato
   - Aprovações expiram após 5 minutos (configurável)
   - Mismatch de hash é detectado e bloqueado

3. **Bloqueio de autorização**:
   - HTTP 401/403 são tratados como bloqueios definitivos
   - Sem retry, sem fallback privilegiado

4. **Journal de auditoria**:
   - Todas as operações são registradas
   - Journal pode persistir em arquivo JSON

### Testes de enforcement

`tests/test_wp053_minimal_privilege_executor.py` contém **32 testes** em 8 classes:

| Classe | Testes | Cobertura |
|--------|--------|-----------|
| TestOperationClassification | 4 | Classificação correta de operações |
| TestProhibitedOperationEnforcement | 7 | Bloqueio de operações proibidas |
| TestApprovalEnforcement | 6 | Validação de aprovações |
| TestAuthorizationBlockEnforcement | 4 | HTTP 401/403 como bloqueio definitivo |
| TestReadOnlyOperations | 2 | Operações de leitura sem aprovação |
| TestJournalAndAudit | 3 | Journal de auditoria |
| TestContextManager | 2 | Gerenciamento de recursos |
| TestBypassAttempts | 4 | Tentativas de bypass bloqueadas |

## Limitações Conhecidas

### LIMITAÇÃO: Sem confinamento real

O executor fornece enforcement de software, mas **não impede bypass** enquanto o agente mantiver acesso ao host privilegiado:

- O agente pode usar `docker exec` para contornar o executor
- O agente pode usar `python3 -c "import sqlite3"` para acessar o banco diretamente
- O agente pode montar o filesystem n8n em um container novo

### Plano de confinamento em etapas

Para isolamento real, são necessárias as seguintes mudanças de infraestrutura:

1. **Etapa 1 — Usuário dedicado sem sudo**:
   - Criar usuário `n8n-operator` sem grupo `docker` ou `sudo`
   - Executar scripts operacionais como este usuário
   - Acesso apenas à API HTTP n8n, não ao filesystem

2. **Etapa 2 — Container isolado**:
   - Container sem Docker socket mount
   - Sem mount do filesystem n8n
   - Acesso apenas à rede Docker do n8n
   - Sem privilégios especiais

3. **Etapa 3 — Secrets management**:
   - API key n8n injetada via variável de ambiente do container
   - Sem acesso a arquivos de configuração do host
   - Rotação automática de credenciais

4. **Etapa 4 — Network policy**:
   - Container do executor só pode acessar n8n na porta 5678
   - Sem acesso a outros serviços na rede
   - Sem acesso à internet externa

### Custo estimado

Zero novos serviços pagos. O confinamento usa recursos Docker existentes:
- Usuário Linux dedicado
- Container com restrições de segurança
- Network policy Docker

## Correção WP-052

A WP-052 relatava "21 testes" em `test_wp052_executor_governance.py`. A contagem real é **21 testes**, confirmada por `pytest --collect-only`. Não há discrepância — o relatório WP-052 estava correto.

## Evidências

### Testes

```
32 tests passed in test_wp053_minimal_privilege_executor.py
```

### Validações pendentes

- `uv run pytest` — suíte completa
- `compileall` — compilação Python
- `git diff --check` — verificação de whitespace

## Riscos

1. **Executor não é barreira física**: sem confinamento real, o executor é uma convenção de software que pode ser ignorada por um agente com acesso ao host
2. **Adoção voluntária**: scripts existentes não usam o executor automaticamente — requer mudança de padrão
3. **Aprovação humana necessária**: operações de escrita exigem aprovação explícita com hash de conteúdo — não é automatizável sem perder segurança

## Próximos passos

1. **WP-054**: Implementar confinamento de container para o executor
2. **WP-055**: Migrar scripts operacionais para usar o executor
3. **WP-056**: Implementar network policy e secrets management

## Referências

- WP-050: E2E sintético completo
- WP-051: Verificação pós-E2E
- WP-052: Política de governança e testes estáticos
- AGENTS.md: Seção "Integração n8n e governança"
