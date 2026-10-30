# Continuidade do desenvolvimento — Codex ou Junie

## Ponto de partida

- Repositório: `fenatodev/business-automation`, branch base `main`.
- Fonte de verdade: GitHub (`AGENTS.md`, `specs/`, `docs/operations/`, CI e PRs).
- A implantação privada de n8n e PostgreSQL **não é** o GitHub; não inferir estado dos serviços de relatórios históricos.
- Codex é opcional e temporário; **Junie deve continuar sem acesso à sessão ou memória do Codex**.
- A aplicação comercial permanece sob gate explícito: não ativar workflows, publicar API nem enviar mensagens sem autorização.

## Primeira sessão de qualquer agente

1. Verificar branch e árvore de trabalho; usar novo worktree da `main` para não sobrescrever trabalho anterior.
2. Ler `AGENTS.md`, os specs das WPs e os PRs abertos antes de implementar.
3. Uma tarefa focada por branch e PR; não desenvolver arquitetura paralela.
4. `uv sync --frozen` em venv próprio do agente, sem assumir que `.venv` do worktree seja válido.
5. Executar `uv run pytest -q`, `uv run python -m compileall -q app tests`, `git diff --check origin/main...HEAD`. Para migrações e concorrência, também testar PostgreSQL descartável.
6. Apresentar evidência com contagem real, riscos, commits e próxima ação; não afirmar E2E PASS com testes unitários.
7. Merge apenas após CI e autorização. Nunca mesclar pelo Junie sem instrução específica.

## Estado técnico no início desta WP

- Pipeline sintético n8n → FastAPI → PostgreSQL validado em ambiente descartável (WP-058); operação real não ativada.
- `/operator` implementa triagem e revisão; resumo e alertas 24h integrados na `main` (WP-059/060).
- WP-061 adicionou contrato de handoff e exclusões de contexto para build Docker. O build sem rede não terminou porque faltava buscar `uv`; validação de build conectado continua separada.
- Codex CLI 0.165.0 instalado no Ubuntu em inspeção anterior; Context Mode bloqueou um toolcall sob aprovação `never` e AgentMemory não teve uso comprovado. **Nenhum deles é dependência do produto**.
- WP-062 (PR deste arquivo): decisão condicional atômica e fila paginada; testes de aplicação aprovados. Concurrency race em PostgreSQL descartável continua sendo gate recomendado antes de exposição real.

## Pontos operacionais obrigatórios antes de ativar clientes

- Revisar backups e restauração do banco real n8n, incluindo chave de criptografia; snapshot não substitui drill.
- Validar autenticação/tenancy no ambiente de destino e revisão humana antes de qualquer saída.
- Confirmar que retries, dedupe e falhas recuperáveis não geram mensagens duplicadas.
- Definir política de retenção, LGPD, métricas e alertas sem PII.
- Não usar API paga, VPS ou exposição pública por inferência; exigir aprovação específica.

## Handoff de cada PR

Registrar objetivo, arquivos, estado (PASS/BLOCKED), comandos e resultados, comportamento em PostgreSQL quando aplicável, riscos, dependências locais, próximo passo concreto e o que **não foi** validado.

## WP-063 — motor interno durável (30/10/2026)

Implementação na branch `wp/063-durable-internal-tasks`; spec reproduzível em
`specs/wp-063-durable-internal-tasks.md`. O novo endpoint persiste triagem
sintética por tenant; worker explícito conclui na fila de revisão humana.
Retries limitados, lease, fencing e deduplicação sobrevivem a novas sessões.
Não há envio externo, ativação n8n nem worker instalado no ambiente principal.

Evidência local: **1119 testes passaram**, dois warnings preexistentes;
`compileall app tests` e `git diff --check` passaram. Harness PostgreSQL 17
**PASS**: upgrade novo/legado, único head, ausência de drift, rejeição de
mapeamento ambíguo, dez corridas de claim, retomada por nova conexão e disputa
entre conclusão sob lock e recuperação. Nenhum banco real foi usado.

Context Mode e AgentMemory responderam nesta sessão; memória retornou busca
vazia. São opcionais, sem dependência de produto. CI/PR continuam como gate de
integração; consultar a branch e checks no GitHub para estado posterior.

Para reproduzir em checkout descartável dessa branch:

```bash
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
DATABASE_URL='sqlite+pysqlite:///:memory:' bash scripts/verify-alembic-postgres.sh
```

O último comando cria seu próprio container efêmero e remove somente esse
container. Não executar migration/worker contra `.env` operacional.
Próximo recorte independente: consulta paginada e resumo de tarefas internas
falhas/atrasadas para o operador. Reprocessamento manual, supervisor 24x7,
retenção e integrações externas continuam pendentes; não afirmar prontidão
comercial nem operação contínua validada em produção.

Limitação de CI: o push do job adicional PostgreSQL foi recusado porque a
credencial GitHub não possui escopo `workflow`. O workflow existente foi
preservado; a suíte offline continua obrigatória no CI. O harness PostgreSQL
passou localmente; execução automática dele no CI permanece PENDENTE até
alteração de workflow por credencial autorizada. Não ampliar escopos por inferência.

## WP-064 — consultas operacionais (30/10/2026)

WP-063 integrada pelo [PR #146](https://github.com/fenatodev/business-automation/pull/146),
commit `f5e869ee3ca9ee75544c543926fd5e6603f41a15`, CI verde e reprodução independente.
A branch `wp/064-internal-task-visibility` acrescenta listagem paginada/filtro e
resumo tenant-scoped das tarefas; detalhes em `specs/wp-064-internal-task-visibility.md`.
Nenhum schema, política de autorização, execução de worker ou serviço real mudou.

Validação local: **1128 testes passaram**, dois warnings preexistentes,
compileall e diff-check PASS. CI existente deve confirmar antes de integração.
Resumo distingue tarefas disponíveis há mais de 24h de retries ainda em espera,
e mostra leases expirados sem recuperá-los como efeito da consulta.

Próxima WP executável: apresentar lista/resumo no `/operator`, usando somente
os endpoints existentes, sem expor payload e sem iniciar worker automaticamente.

## WP-065 — paginação segura da fila de revisão (30/10/2026)

[PR #148](https://github.com/fenatodev/business-automation/pull/148),
branch `wp/065-review-pagination-route`, commit `b14f79a`.
A allowlist do JavaScript rejeitava `/review-queue/?limit=50&offset=0`,
quebrando a própria paginação. Correção com validação estrita de tipo,
caracteres de controle e regex para limit (1-100) e offset (0+).
**1129 testes passaram**; compileall, node --check, diff-check: PASS.
CI verde.

## WP-066 — painel de tarefas internas (30/10/2026)

[PR #149](https://github.com/fenatodev/business-automation/pull/149),
branch `wp/066-internal-task-panel`, commit `0ac0eb5`.
Painel "Tarefas internas" no `/operator` com lista, filtro por status,
resumo de contagens e botão atualizar. `taskApi()` com allowlist estrita.
**1129 testes passaram**; compileall, node --check, diff-check: PASS.
CI verde.

## WP-067 — retry manual e retenção (30/10/2026)

[PR #151](https://github.com/fenatodev/business-automation/pull/151),
branch `wp/067-task-retry-retention`.
Retry manual de tarefas falhadas (`POST /{task_id}/retry`) e retenção
configurável (`POST /retention`) para purgar tarefas terminadas antigas.
Operador-only, tenant-isolado. Sem migration.
**1136 testes passaram**; compileall, diff-check: PASS.

## WP-068 — supervisor 24×7 (30/10/2026)

Branch `wp/068-supervisor-24x7`.
Loop contínuo sobre `run_once()` com polling configurável, shutdown graceful
(SIGTERM/SIGINT) e estatísticas de saúde (ciclos, tarefas, erros).
Script CLI standalone em `scripts/run_supervisor.py`.
**1136 testes passaram**; compileall, diff-check: PASS.

Próximo recorte: avaliar integrações externas (n8n workflow activation, etc).
