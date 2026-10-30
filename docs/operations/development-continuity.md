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

## WP-078 — Busca e filtro de conversas (30/10/2026)

Adiciona filtros por canal, status e busca por keywords nas conversas do
operador. `GET /companies/{company_id}/conversations` aceita parâmetros
opcionais `channel`, `status` e `q` (busca case-insensitive em mensagens).
UI com dropdowns de canal/status, campo de busca e botão limpar.
`conversationApi()` atualizada para aceitar query params via `buildConversationUrl()`.
**1197 testes passaram**; compileall, diff-check: PASS.

## WP-079 — Paginação de conversas (30/10/2026)

Adiciona paginação limit/offset ao endpoint de listagem de conversas e um
endpoint de contagem para os controles de paginação da UI.
`GET /companies/{company_id}/conversations` aceita `limit` (default 50, max 100)
e `offset` (default 0). `GET /companies/{company_id}/conversations/count`
retorna `{"total": N}` respeitando os filtros existentes.
UI com botões Anterior/Próxima e indicador de página.
**1211 testes passaram**; compileall, diff-check: PASS.

## WP-080 — Ordenação de conversas (30/10/2026)

`GET /companies/{company_id}/conversations` aceita `sort` (default "last_message").
Opções: last_message (subquery max(Message.created_at)), created_at (desc),
id (asc). Valor inválido decai para ID. UI com dropdown "Ordenar".
**1220 testes passaram**; compileall, diff-check: PASS.

## WP-081 — Fechar conversas (30/10/2026)

Novo endpoint PATCH /conversations/{id} com body {"status": "open"|"closed"}
permite ao operador fechar e reabrir conversas. UI com botão "Fechar" que
alterna entre open/closed. Filtro e count por status já existentes funcionam
com o novo endpoint.
**1229 testes passaram**; compileall, diff-check: PASS.

## WP-082 — Dashboard de métricas (30/10/2026)

Novo endpoint GET /internal-tasks/dashboard agrega contagens tenant-isoladas
de oportunidades (por next_action), conversas (por status), leads (por status),
tarefas internas e review queue. UI com cards de métricas no topo do painel
do operador, carregada automaticamente ao conectar.
**1240 testes passaram**; compileall, diff-check: PASS.

## WP-083 — Gerenciamento de leads no operador (30/10/2026)

Seção "07 / LEADS" no painel do operador com lista de leads, filtro por status
e seletor inline para atualizar status rapidamente. Backend com filtro opcional
`status` em `GET /leads`. `leadApi()` com allowlist estrita; renderização com
`textContent`/`appendChild` (sem innerHTML).
**1268 testes passaram**; compileall, diff-check: PASS.

## WP-084 — Approve e reject do proposal brief (30/10/2026)

Endpoints PATCH /proposal-brief/approve e /proposal-brief/reject. Approve
é atômico (brief → approved, opportunity → in_progress). Reject volta brief
para draft sem alterar opportunity. UI com botões "Aprovar" e "Rejeitar"
no painel de brief, visíveis conforme status.
**1279 testes passaram**; compileall, diff-check: PASS.

## WP-085 — Converter lead em customer via UI (30/10/2026)

Botão "Converter" na seção de leads do operador. Conecta ao endpoint existente
`POST /leads/{lead_id}/convert` (customers.py). Confirmação antes da conversão;
botão oculto para leads já convertidos (status "won"). Tratamento de 409
(duplicata) e 403 (auth).
**1297 testes passaram**; compileall, diff-check: PASS.

## WP-086 — Lista de customers no operador (30/10/2026)

Seção "08 / CUSTOMERS" no painel do operador com lista de customers ativos.
Exibe nome, telefone, email e lead de origem. `customerApi()` com allowlist
estrita; renderização com `textContent`/`appendChild`. Carregamento automático
ao conectar.
**1323 testes passaram**; compileall, diff-check: PASS.

## WP-087 — Visão detalhada de customer com conversas (30/10/2026)

Clicar em um customer na lista abre painel de detalhes com informações e
conversas associadas. Backend com filtro `customer_id` em
`GET /companies/{company_id}/conversations` e count endpoint. UI com
`showCustomerDetail()`, `loadCustomerConversations()` e botão voltar.
**1349 testes passaram**; compileall, diff-check: PASS.

## WP-088 — Notas em leads via UI do operador (30/10/2026)

Textarea "Notas" em cada lead permite ao operador registrar informações
sobre interações. Reutiliza o campo `interest` existente (sem migration).
`LeadUpdate` schema com `interest` e `status` opcionais; backend atualiza
condicionalmente. Salvamento automático no evento `change`.
**1363 testes passaram**; compileall, diff-check: PASS.

## WP-089 — Criar conversa a partir de customer (30/10/2026)

Botão "+ Nova conversa" no painel de detalhes do customer. Prompt para
canal (whatsapp, instagram, web, telegram, email); validação de allowlist.
POST /conversations com customer_id vinculado. Recarrega a lista de
conversas após criação.
**1377 testes passaram**; compileall, diff-check: PASS.

## WP-090 — Arquivamento visual de oportunidades (30/10/2026)

Toggle "Exibir arquivadas" na lista de oportunidades oculta por padrão
as oportunidades com status `done`/`lost`. Backend com `exclude_archived`
query param em `GET /opportunities`. Schema `OpportunityTriageUpdate`
com `in_progress`, `done`, `lost` como opções de triagem.
**1393 testes passaram**; compileall, diff-check: PASS.

## WP-091 — Badge de pendentes no operador (30/10/2026)

Badge vermelho ao lado de "Oportunidades" mostra contagem de oportunidades
com status `pending`. Atualizado automaticamente em `refreshList()`.
**1404 testes passaram**; compileall, diff-check: PASS.

## WP-092 — Labels de status de oportunidades no operador (30/10/2026)

Os status `in_progress`, `done` e `lost` foram adicionados ao backend
(WP-073/074) mas os labels em `actionLabels` do JavaScript não foram
atualizados, fazendo o operador ver "Estado desconhecido". Corrigido
adicionando os três labels faltantes.
**1414 testes passaram**; compileall, diff-check: PASS.

## WP-093 — Editar título e descrição de oportunidades (30/10/2026)

Painel de edição inline no painel de triagem permite ao operador alterar
título e descrição das oportunidades. Backend com `PATCH /opportunities/{id}`
tenant-isolado. Validação de comprimento e campos obrigatórios.
**1436 testes passaram**; compileall, diff-check: PASS.
