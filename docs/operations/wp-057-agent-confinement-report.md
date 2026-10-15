# WP-057 — Confinar Junie Brave sem interromper IDE ou n8n

**Status**: CONCLUÍDO (Fase A — sem alterar host)
**Branch**: `wp/057-agent-confinement`
**Testes**: 1037 passando (86 novos)

## Implementado

### 1. Sandbox do Agente Junie (ops/agent-sandbox/)

Diferente do `ops/sandbox/` que isola apenas o executor n8n, o `ops/agent-sandbox/` isola o **processo do agente Junie inteiro**:

- **Dockerfile**: Container Python 3.12-slim com usuário não-root (`junie-agent`), sem grupos docker/sudo/lxd, bubblewrap para sandbox mode do Junie, sem montagem de Docker socket, n8n data, home do usuário, SSH agent ou ~/.config
- **docker-compose.yml**: Read-only filesystem, no-new-privileges, sem rede por padrão, rede interna definida mas não conectada, resource limits (1 CPU, 512MB), sem portas expostas
- **sandbox.json**: Política completa de isolamento — MCP denial por padrão (Playwright, Computer Use, etc.), rede restrita (sem sockets Unix, redes internas bloqueadas), sistema de arquivo com deny read/write para diretórios sensíveis, brave mode off, sandbox mode on
- **launch-agent.sh**: Launcher com verificações de isolamento — falha se Docker socket, LXD, home do usuário, n8n data ou SSH agent estiverem acessíveis; autenticação via JUNIE_API_KEY (não sessão do navegador); Git token reduzido opcional
- **healthcheck.py**: Healthcheck que verifica todos os caminhos de isolamento — Docker socket, LXD, home, n8n, SSH agent, usuário não-root, filesystem read-only

### 2. Diferenciação IDE vs CLI

A investigação revelou diferenças críticas:

| Aspecto | Junie CLI | Junie IDE (PyCharm) |
|---------|-----------|---------------------|
| Processo | Standalone no terminal | Plugin dentro da IDE |
| Sandbox | `--sandbox` com srt (Anthropic) | Não disponível em release builds |
| Autenticação | JUNIE_API_KEY, browser, BYOK | Sessão do navegador |
| Ollama | Suportado | Não suportado |
| Acesso ao host | Controlável via sandbox | Acesso total do host |

**Conclusão**: O Junie da IDE **não é** o mesmo processo que o CLI. Configurar o CLI não confina o Junie da IDE. O sandbox mode (`--sandbox`) está disponível apenas no CLI e apenas em builds development/nightly/experimental.

### 3. Testes de Isolamento (86 novos)

| Classe | Contagem | Cobertura |
|--------|----------|-----------|
| `TestDockerfileIsolation` | 14 | Non-root, sem grupos privilegiados, sem mounts sensíveis |
| `TestDockerComposeIsolation` | 14 | Read-only, no-new-privileges, sem rede host, resource limits |
| `TestSandboxConfig` | 15 | MCP denial, rede restrita, filesystem limits, brave off |
| `TestLauncherScript` | 10 | Verificações de isolamento, auth, Git token |
| `TestHealthcheck` | 8 | Todos os checks de isolamento |
| `TestBypassAttempts` | 11 | Docker, LXD, sudo, n8n DB, secrets, SSH, MCP, rede |
| `TestIDEvsCLI` | 5 | Diferenciação IDE vs CLI, IDE não afetado |
| `TestDockerComposeSyntax` | 4 | Validação de sintaxe do compose |
| `TestHealthcheckExecution` | 6 | Execução real do healthcheck |

## Prova de Isolamento

Os testes comprovam que a configuração do sandbox:

1. **Bloqueia Docker socket** — `/var/run/docker.sock` não é montado
2. **Bloqueia LXD** — `/var/lib/lxd` não é montado
3. **Bloqueia sudo** — usuário não está no grupo sudo
4. **Bloqueia n8n SQLite** — `/var/lib/n8n` não é legível
5. **Bloqueia segredos** — `~/.config`, `~/.junie` não são legíveis
6. **Bloqueia SSH keys** — `~/.ssh` não é legível
7. **Bloqueia MCPs de host** — Playwright, Computer Use, etc. negados por padrão
8. **Bloqueia rede interna** — 127.0.0.1, 172.16.0.0/12, 192.168.0.0/16, 10.0.0.0/8
9. **Filesystem read-only** — apenas /workspace, /var/log/junie-agent, /tmp são graváveis
10. **Usuário não-root** — sem privilégios elevados

## Limitações

1. **Gate B pendente**: Container preparado mas NÃO aplicado — requer aprovação explícita para `docker compose up`
2. **Junie CLI sandbox mode**: Disponível apenas em builds development/nightly/experimental — não em EAP/release
3. **Junie IDE não isolado**: O plugin da IDE roda com acesso total ao host — este sandbox isola apenas o CLI
4. **Autenticação Junie**: Requer JUNIE_API_KEY injetada — não funciona com sessão do navegador no container
5. **Git access**: Requer token reduzido ou Git transfer mediado — SSH agent não é montado
6. **Isolamento do Junie no host atual**: Se o Junie roda no host com shell privilegiado (grupos docker/sudo/lxd), este sandbox não o confina — é um container separado para execução futura

## Bloqueios

- **Nenhuma modificação** no n8n runtime, Docker runtime, credenciais, permissões do host ou produção
- **Nenhum usuário criado**, grupo alterado, ou permissão modificada no host
- **Container não aplicado** — apenas Dockerfile/compose preparados e validados com `docker compose config`

## Próxima Ação (Gate B)

Para aplicar o isolamento:

1. Criar usuário dedicado sem grupos docker/sudo/lxd
2. Gerar JUNIE_API_KEY com escopo reduzido
3. Gerar Git token com escopo reduzido (repo:status, repo:content)
4. Aplicar `docker compose -f ops/agent-sandbox/docker-compose.yml up -d`
5. Validar healthcheck e isolamento no container
6. Testar Junie CLI no container com tarefa sintética
