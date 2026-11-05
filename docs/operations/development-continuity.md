# Continuidade do desenvolvimento — Codex ou Junie

## Ponto de partida

- Repositório: `fenatodev/business-automation`, branch base `main`.
- Fonte de verdade: GitHub (`AGENTS.md`, `specs/`, `docs/operations/`, CI e PRs).
- A implantação privada de n8n e PostgreSQL **não é** o GitHub; não inferir estado dos serviços de relatórios históricos.
- Codex é opcional e temporário; **Junie deve continuar sem acesso à sessão ou memória do Codex**.
- A aplicação comercial permanece sob gate explícito: não ativar workflows, publicar API nem enviar mensagens sem autorização.

## Esteira local contínua do Codex

O desenvolvimento contínuo local usa `scripts/continuous-dev-loop.sh`, que
inicia uma execução independente do Codex CLI por WP. O prompt operacional
está em `scripts/continuous-dev-task.md`; cada execução termina após uma WP,
um bloqueio real ou a ausência de uma WP segura.

O supervisor trabalha somente em árvore limpa na `main`, não inicia outra WP
enquanto houver PR `wp/*` aberto, preserva logs em
`/tmp/business-automation-codex-loop/` e usa backoff progressivo para falhas
transitórias. Ele não apaga alterações locais, não usa `git reset --hard` ou
`git clean`, e respeita `/tmp/business-automation.stop`.

Para executar uma vez:

```bash
scripts/continuous-dev-loop.sh --once
```

Para iniciar o ciclo contínuo:

```bash
rm -f /tmp/business-automation.stop
scripts/continuous-dev-loop.sh
```

Para parar sem apagar nada:

```bash
touch /tmp/business-automation.stop
```

O supervisor usa Codex CLI 0.165.0 com `--sandbox danger-full-access` e
`approval_policy="never"`, conforme as flags disponíveis localmente. O modo
`--dry-run` apenas registra a execução planejada; a validação normal continua
exigindo árvore limpa, autenticação GitHub e ausência de PR aberto.

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

## WP-094 — Busca de oportunidades por keywords (30/10/2026)

Campo de busca na toolbar de oportunidades filtra por título e descrição
(case-insensitive). Backend com `?q=` query param em `GET /opportunities`.
Combina com `exclude_archived` para filtragem composta.
**1453 testes passaram**; compileall, diff-check: PASS.

## WP-095 — Ordenação e paginação de oportunidades (31/10/2026)

O módulo de oportunidades não tinha ordenação configurável nem paginação,
dificultando o trabalho com carteiras grandes. Adicionado `sort` param
(id, created_at, next_action), `limit`/`offset` paginação e endpoint
`GET /opportunities/count`. UI com dropdown "Ordenar" e controles
Anterior/Próxima com indicador de página.
**1468 testes passaram**; compileall, diff-check: PASS.

## WP-096 — Persistência de intake comercial (31/10/2026)

O backend de intake tinha apenas o endpoint evaluate (simulação).
Adicionado `POST /internal/commercial-intake/create` que avalia o intake
e persiste automaticamente como Opportunity com deduplicação por event_id
e isolamento de tenant. UI com seção "09 / INTAKE COMERCIAL" no painel
do operador: formulário com canal, ID do evento e mensagem; exibição da
decisão (intenção, revisão humana, flags, ID da oportunidade criada).
**1478 testes passaram**; compileall, diff-check: PASS.

## WP-097 — Review queue aprovação cria oportunidade (31/10/2026)

Aprovar um item na review queue não criava oportunidade, quebrando o
fluxo review → opportunity. Modificado `apply_decision` em
`commercial_pipeline.py` para criar Opportunity automaticamente ao
aprovar, com deduplicação por event_id e isolamento de tenant.
Rejeitar não cria oportunidade. Schema com source "review_queue".
**1484 testes passaram**; compileall, diff-check: PASS.

## WP-098 — Feedback de oportunidade na review queue (31/10/2026)

Aprovar um item na review queue criava oportunidade automaticamente (WP-097),
mas não informava ao operador qual foi criada. Modificado `apply_decision`
para retornar a `opportunity_id` criada, e a UI agora mostra a oportunidade
criada e atualiza a lista automaticamente. Rejeitar retorna `opportunity_id: null`.
**1494 testes passaram**; compileall, diff-check: PASS.

## WP-099 — Busca de leads por keywords (31/10/2026)

O módulo de leads tinha filtro por status mas não tinha busca por keywords.
Adicionado parâmetro `?q=` em `GET /leads` com busca case-insensitive em
nome e interesse. UI com campo de busca inline que filtra em tempo real.
**1503 testes passaram**; compileall, diff-check: PASS.

## WP-100 — Paginação de leads no operador (31/10/2026)

O módulo de leads não tinha paginação. Adicionado `limit`/`offset` em
`GET /leads` e novo `GET /leads/count`. UI com controles Anterior/Próxima
e indicador de página. **1527 testes passaram**; compileall, diff-check: PASS.

## WP-101 — Ordenação de leads no operador (31/10/2026)

O módulo de leads não tinha ordenação configurável. Adicionado parâmetro
`sort` em `GET /leads` (id, created_at, status). UI com dropdown "Ordenar".
**1527 testes passaram**; compileall, diff-check: PASS.

## WP-103 — Consolidação da main (31/10/2026)

As WPs da WP-078 à WP-101 foram merged em cadeia nas branches WP, não na
main. A main ficou com versão antiga do código enquanto os testes antigos
permaneciam. Esta WP consolida todas as mudanças na main: remove testes UI
obsoletos substituídos pela versão unificada (WP-077), adiciona filtro
`next_action` e endpoint `pipeline-summary` ao router de oportunidades,
corrige `test_client0_simulation.py` para usar `/approve` dedicado e
atualiza `test_operator_ui.py` para refletir botões approve/reject.
**1555 testes passaram**; compileall, diff-check: PASS.

## WP-104 — Busca, ordenação e paginação de customers (31/10/2026)

O módulo de customers não tinha busca, ordenação configurável nem paginação.
Adicionado `?q=` em `GET /customers` com busca case-insensitive em nome,
telefone e email. Ordenação por `sort` (id, created_at, name). Paginação
com `limit`/`offset` e novo `GET /customers/count`. UI com campo de busca,
dropdown "Ordenar" e controles Anterior/Próxima.
**1572 testes passaram** (17 novos); compileall, diff-check: PASS.

## WP-105 — Triagem em massa de oportunidades (31/10/2026)

O operador só podia triar uma oportunidade de cada vez. Adicionado
`POST /opportunities/bulk-triage` que aceita múltiplos IDs (1-100) e
aplica a mesma ação de triagem tenant-isolada. UI com checkboxes em
cada oportunidade, barra de triagem em massa com contador, seletor de
ação, nota opcional e botões aplicar/limpar.
**1588 testes passaram** (16 novos); compileall, diff-check: PASS.

## WP-106 — Exportação CSV de dados do operador (31/10/2026)

O operador não podia exportar dados para análise externa. Adicionado
`GET /opportunities/export.csv`, `GET /leads/export.csv` e
`GET /customers/export.csv` — endpoints tenant-isolados que retornam
arquivos CSV com cabeçalhos em português. UI com botão "Exportar CSV"
nas seções de oportunidades, leads e customers.
**1587 testes passaram** (15 novos); compileall, diff-check: PASS.

## WP-107 — Notificações visuais no operador (31/10/2026)

Sino 🔔 na barra superior agrega contagens de oportunidades pendentes,
leads novos e conversas abertas. Polling automático a cada 30 segundos.
Tooltip detalhado ao passar o mouse.
**1588 testes passaram**; compileall, diff-check: PASS.

## WP-108 — Painel de detalhes da oportunidade (31/10/2026)

`selectOpportunity()` sempre carrega o brief (independentemente do
status). Novos metadados: fonte, capturada em, nota de triagem.
Botão "Ver brief" com scroll suave.
**1579 testes passaram** (18 testes UI); compileall, diff-check: PASS.

## WP-109 — Exportação CSV de conversas (31/10/2026)

`GET /companies/{company_id}/conversations/export.csv` tenant-isolado
com mensagens concatenadas. Botão "Exportar CSV" na UI.
**1590 testes passaram** (7 testes backend); compileall, diff-check: PASS.

## WP-110 — Editar customer via UI (31/10/2026)

`PATCH /customers/{id}` tenant-isolado com `CustomerUpdate` schema
parcial. Formulário inline no painel de detalhes com botão "✏️ Editar".
**1589 testes passaram** (26 testes); compileall, diff-check: PASS.

## WP-111 — Criar customer manualmente (31/10/2026)

Formulário "Novo customer" na seção de customers. Reusa `POST /customers`
existente.
**1594 testes passaram** (15 testes); compileall, diff-check: PASS.

## WP-112 — Criar lead manualmente (31/10/2026)

Formulário "Novo lead" na seção de leads com nome, telefone, fonte e
interesse. Reusa `POST /leads` existente.
**1598 testes passaram** (17 testes); compileall, diff-check: PASS.

## WP-113 — Notas em oportunidades (31/10/2026)

`triage_note` adicionado ao `OpportunityUpdate` schema; PATCH com
`exclude_unset` para suporte a nulo explícito. UI com painel standalone
no detalhe da oportunidade.
**1580 testes passaram** (21 testes); compileall, diff-check: PASS.

## WP-114 — Detalhes expandidos de lead (31/10/2026)

Painel clicável mostrando nome, telefone, fonte, interesse, data e
conversas associadas — seguindo o padrão do customer detail.
**1585 testes passaram** (18 testes); compileall, diff-check: PASS.

## WP-115 — Status em massa de leads (31/10/2026)

`POST /leads/bulk-status` com 1-100 IDs tenant-isolado. UI com
checkboxes e barra de status em massa.
**1593 testes passaram** (8 testes); compileall, diff-check: PASS.

## WP-117 — Correção do script de demonstração Client 0 (31/10/2026)

O passo 14 do script demo_client0_cycle.sh estava comentado. Agora
fecha a oportunidade como "done" completando o ciclo F2 inteiro.
**1733 testes passaram**; compileall, diff-check: PASS.

## WP-118 — Badges visuais coloridos nas oportunidades (31/10/2026)

Indicadores coloridos: pendente (amarelo), acompanhar (azul), proposta
(roxo), em andamento (verde), concluída (verde claro), perdida
(vermelho), ignorado (cinza).
**1742 testes passaram**; compileall, diff-check: PASS.

## WP-119 — Badges visuais estendidos (31/10/2026)

Badges para conversas (aberta/fechada) e leads (novo, contactado,
qualificado, perdido, convertido).
**1751 testes passaram** (36 novos); compileall, diff-check: PASS.

## WP-120 — Seção completa de tarefas internas (31/10/2026)

Seção "10 / TAREFAS INTERNAS" com lista, filtro por status, ordenação
(id, created_at, status, attempts), paginação e botão retry para
tarefas falhadas. Backend com `sort` em list_tasks e novo
`GET /internal-tasks/count`.
**1803 testes passaram** (34 testes); compileall, diff-check: PASS.

## WP-121 — Exportação CSV da review queue (31/10/2026)

`GET /review-queue/export.csv` tenant-isolado e botão "Exportar CSV"
na UI.
**1810 testes passaram** (7 testes); compileall, diff-check: PASS.

## WP-122 — Exportação CSV das tarefas internas (31/10/2026)

`GET /internal-tasks/export.csv` tenant-isolado e botão "Exportar CSV"
na seção de tarefas. Completa a cobertura de exportação CSV em todos
os módulos.
**1815 testes passaram** (5 testes); compileall, diff-check: PASS.

## WP-123 — Exportação CSV filtrada das oportunidades (31/10/2026)

O endpoint `GET /opportunities/export.csv` agora respeita os mesmos
filtros que a lista: `next_action`, `q` (busca) e `exclude_archived`.
**1822 testes passaram** (7 testes); compileall, diff-check: PASS.

## WP-124 — Consolidação de WP-120 a WP-123 (31/10/2026)

4 PRs abertos (WP-120 a WP-123) criados da mesma base main teriam
conflitos de merge sequencial. Branch consolidada que combina
manualmente todas as mudanças das 4 WPs em um único commit.
**1822 testes passaram**; compileall, diff-check: PASS.
PR #208: https://github.com/fenatodev/business-automation/pull/208

## WP-130 — Fonte configurável na captura manual (31/10/2026)

O formulário de captura manual tinha a fonte hardcodeada como "99freelas".
Adicionado dropdown com opções: manual, 99freelas, intake, review_queue.
**1839 testes passaram**; compileall, diff-check: PASS.
PR #209: https://github.com/fenatodev/business-automation/pull/209

## WP-131 — Filtro e ordenação na review queue (31/10/2026)

A review queue só listava itens pendentes. Adicionado filtro por status
e ordenação configurável (id, created_at, status). Novo endpoint /count.
**1853 testes passaram**; compileall, diff-check: PASS.
PR #210: https://github.com/fenatodev/business-automation/pull/210

## WP-132 — Paginação de mensagens em conversas (31/10/2026)

O endpoint GET /conversations/{id}/messages carregava todas as mensagens
de uma vez. Adicionado limit (default 50, max 100) e offset (default 0).
Novo endpoint /count para controles de paginação.
**1863 testes passaram** (10 novos); compileall, diff-check: PASS.
PR #211: https://github.com/fenatodev/business-automation/pull/211

## WP-133 — Validação de transições de status (31/10/2026)

O endpoint de triagem permitia qualquer transição de status. Adicionado
_VALID_TRANSITIONS definindo o ciclo F2: done/lost/ignore são estados
terminais; in_progress é obrigatório antes de done/lost. Bulk triage
pula oportunidades com transição inválida.
**1874 testes passaram** (11 novos); compileall, diff-check: PASS.
PR #212: https://github.com/fenatodev/business-automation/pull/212

## WP-134 — Filtros e ordenação na review queue UI (31/10/2026)

A review queue na UI tinha paginação mas não tinha filtros visíveis de
status e ordenação. Adicionado dropdown de status (Todos, Pendente,
Aprovado, Rejeitado), dropdown de ordenação (Data, ID, Status) e botão
Limpar. buildReviewUrl() e buildReviewCountUrl() conectam os filtros
ao backend. reviewApi allowlist atualizada para /count e query params.
**1891 testes passaram** (17 novos); compileall, diff-check: PASS.
PR #213: https://github.com/fenatodev/business-automation/pull/213

## WP-135 — Remover ordenação client-side de conversas (31/10/2026)

`showConversationList()` ordenava as conversas no navegador, ignorando a
ordem retornada pelo backend. Removida a ordenação client-side redundante;
a função agora preserva a ordem do backend. O dropdown `conv-filter-sort`
já estava conectado a `buildConversationUrl()` — a correção garante que a
ordem escolhida pelo operador seja respeitada.
**1906 testes passaram** (15 novos); compileall, diff-check: PASS.
PR #214: https://github.com/fenatodev/business-automation/pull/214

## WP-136 — Paginação de mensagens em conversas na UI (31/10/2026)

selectConversation() carregava todas as mensagens de uma conversa sem
paginação. loadMessages() agora usa limit/offset e /count em paralelo,
segundo o padrão dos outros módulos. Controles de paginação (Anterior/Próxima)
adicionados no detalhe da conversa. allowlist atualizada para /messages/count.
**1923 testes passaram** (17 novos); compileall, diff-check: PASS.
PR #215: https://github.com/fenatodev/business-automation/pull/215

## WP-137 — Auto-refresh do dashboard e polling de notificações (31/10/2026)

O dashboard só atualizava manualmente e as notificações não tinham polling
real. startDashboardRefresh() inicia polling a cada 60s;
startNotificationRefresh() a cada 30s para atualizar o badge pendente.
Ambos são parados no disconnect().
**1938 testes passaram** (15 novos); compileall, diff-check: PASS.
PR #216: https://github.com/fenatodev/business-automation/pull/216

## WP-138 — Opções completas no select de triagem individual (31/10/2026)

O formulário de triagem individual tinha apenas 4 opções (pending, follow,
ignore, prepare_proposal), mas o backend OpportunityTriageUpdate suporta 7
(incluindo in_progress, done, lost). O select de triagem em massa já estava
correto. Adicionadas as 3 opções faltantes ao select individual, alinhando
com o backend e com o bulk triage.
**1953 testes passaram** (15 novos); compileall, diff-check: PASS.

## WP-139 — Filtro de pipeline visual no operador (31/10/2026)

A funcionalidade de pipeline summary (WP-072) foi perdida na consolidação.
Adicionados chips clicáveis de pipeline na toolbar de oportunidades: cada
chip mostra status e contagem via /opportunities/pipeline-summary. Ao clicar,
o filtro next_action é aplicado à lista. 7 chips: Todas, Pendente, Acompanhar,
Proposta, Em andamento, Concluída, Perdida.
**1972 testes passaram** (19 novos); compileall, diff-check: PASS.

## WP-140 — Notas internas em conversas (31/10/2026)

O operador não podia registrar notas internas em conversas. Adicionado campo
`note` opcional ao schema `ConversationUpdate`. Ao salvar, a nota é armazenada
como mensagem com `sender_type="system"` e prefixo "📝 Nota interna: ", evitando
migration. Endpoint `GET /conversations/{id}/note` retorna a nota mais recente.
UI com campo de nota no painel de detalhes da conversa.
**1983 testes passaram** (11 novos); compileall, diff-check: PASS.

## WP-141 — Operações em massa em conversas (31/10/2026)

O operador só podia fechar/reabrir uma conversa de cada vez. Novo endpoint
`POST /conversations/bulk-status` aceita 1-100 IDs e atualiza status
(open/closed) de forma tenant-isolada. UI com checkboxes na lista e barra
de ação em massa.
**1991 testes passaram** (8 novos); compileall, diff-check: PASS.

## WP-142 — Conversas relacionadas à oportunidade (31/10/2026)

O painel de detalhes da oportunidade não mostrava as conversas da mesma
company. Adicionado endpoint `GET /opportunities/{id}/conversations` que
retorna até 50 conversas tenant-isoladas, ordenadas por ID descendente.
UI com seção "Conversas relacionadas" no painel de detalhes; itens
clicáveis navegam para a seção de conversas.
**1999 testes passaram** (8 novos); compileall, diff-check: PASS.

## WP-143 — Timeline de atividades da oportunidade (31/10/2026)

O operador não via o histórico de ações em uma oportunidade. Adicionado
endpoint `GET /opportunities/{id}/timeline` que deriva eventos dos dados
existentes: criação, triagem (com nota) e mudanças de status do brief.
Sem migration — usa apenas Opportunity e ProposalBrief. UI com seção
"Atividades" no painel de detalhes.
**2008 testes passaram** (9 novos); compileall, diff-check: PASS.

## WP-144 — Leads relacionados à oportunidade (31/10/2026)

O painel de detalhes da oportunidade não mostrava os leads da mesma company.
Adicionado endpoint `GET /opportunities/{id}/leads` que retorna até 50 leads
tenant-isolados, ordenados por ID descendente. UI com seção "Leads relacionados"
no painel de detalhes.
**2016 testes passaram** (8 novos); compileall, diff-check: PASS.

## WP-146 — Atalhos de teclado no operador (31/10/2026)

O operador dependia inteiramente do mouse para navegar. Adicionados atalhos
de teclado: Ctrl+K foca o campo de busca de oportunidades; Escape limpa
a seleção atual. Indicação dos atalhos no rodapé.
**2016 testes passaram**; compileall, diff-check: PASS.

## WP-147 — Criar lead a partir de conversa (31/10/2026)

O operador via conversas mas não podia criar um lead diretamente a partir
delas. Botão "+ Criar lead desta conversa" no painel de detalhes abre
formulário inline com nome, telefone, fonte e interesse. A fonte é pré-
preenchida com o canal da conversa. Após criar, a lista de leads é
atualizada automaticamente.
**2016 testes passaram**; compileall, diff-check: PASS.

## WP-148 — Contagem de mensagens nas conversas da oportunidade (31/10/2026)

O painel de detalhes da oportunidade listava conversas relacionadas (WP-142)
mas não indicava quantas mensagens cada uma tinha. `loadOpportunityConversations()`
agora carrega contagens em paralelo via `/messages/count` e exibe "N msg"
ao lado do status de cada conversa.
**2016 testes passaram**; compileall, diff-check: PASS.

## WP-149 — Filtro de data em oportunidades (31/10/2026)

O módulo de oportunidades não tinha filtro por data. Adicionado `from_date`
e `to_date` query params em `GET /opportunities`, `GET /opportunities/count`
e `GET /opportunities/export.csv`. Usa comparação de strings ISO 8601
(`captured_at >= from_date`) compatível com SQLite e PostgreSQL.
**2024 testes passaram** (8 novos); compileall, diff-check: PASS.

## WP-150 — Filtro de data em oportunidades na UI (31/10/2026)

A WP-149 adicionou `from_date`/`to_date` ao backend, mas a UI não tinha
campos para usá-los. Adicionados dois campos de data (de/até) na toolbar
de oportunidades, conectados a `refreshList()` e count endpoint. Botão
"Limpar filtros" reseta todos os filtros (busca, data, ordenação,
arquivadas, pipeline). Exportação CSV respeita os filtros de data.
**2042 testes passaram** (18 novos); compileall, diff-check: PASS.

## WP-151 — Filtro de data em conversas (31/10/2026)

O módulo de conversas não tinha filtro por data. Adicionado `from_date`
e `to_date` em list, count e export CSV. UI com campos de data na seção
de filtros. **2049 testes passaram** (7 novos); compileall, diff-check: PASS.

## WP-152 — Filtro de data em leads (31/10/2026)

O módulo de leads não tinha filtro por data. Adicionado `from_date`
e `to_date` em list, count e export CSV. UI com campos de data na seção
de filtros. Exportação CSV respeita os filtros de data.
**2057 testes passaram** (8 novos); compileall, diff-check: PASS.

## WP-153 — Filtro de data em customers (31/10/2026)

O módulo de customers não tinha filtro por data. Adicionado `from_date`
e `to_date` em list, count e export CSV. UI com campos de data na seção
de filtros. Exportação CSV respeita os filtros de data.
**2063 testes passaram** (6 novos); compileall, diff-check: PASS.

## WP-154 — Filtro de data em review queue (31/10/2026)

A review queue não tinha filtro por data. Adicionado `from_date`
e `to_date` em list, count e export CSV. UI com campos de data na seção
de filtros. Exportação CSV respeita os filtros de data.
**2075 testes passaram** (12 novos); compileall, diff-check: PASS.

## WP-155 — Filtro de data em internal tasks (31/10/2026)

O módulo de internal tasks não tinha filtro por data. Adicionado `from_date`
e `to_date` em list, count e export CSV. Service layer atualizado para
suportar os parâmetros. UI com campos de data na seção de filtros.
Exportação CSV respeita os filtros de data.
**2075 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-156 — Exibir orçamento e descrição na lista de oportunidades

A lista de oportunidades mostrava apenas ID, título e status. `renderList()`
agora exibe descrição truncada (120 caracteres) e linha de metadados com
orçamento (💰) e prazo (📅) quando presentes. Sem mudança no backend.
**2091 testes passaram** (16 novos); compileall, diff-check: PASS.

### WP-157 — Importação CSV de leads

O operador só podia criar leads manualmente um por um. `POST /leads/import.csv`
aceita CSV com Nome, Telefone, Fonte e Interesse. Deduplicação por telefone,
tenant isolation, limite de 500 linhas. Botão "Importar CSV" na UI.
**2103 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-158 — Importação CSV de customers

O operador só podia criar customers manualmente um por um. `POST /customers/import.csv`
aceita CSV com Nome, Telefone e E-mail (opcional). Deduplicação por telefone,
tenant isolation, limite de 500 linhas. Botão "Importar CSV" na UI.
**2115 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-159 — Importação CSV de oportunidades

O operador só podia registrar oportunidades manualmente uma por uma.
`POST /opportunities/import.csv` aceita CSV com Título, Descrição, URL (opcional),
Orçamento, Prazo e Requisitos. Deduplicação por external_url, tenant isolation,
limite de 500 linhas. Botão "Importar CSV" na UI. `source="import"` adicionado
ao OpportunityCreate Literal.
**2129 testes passaram** (14 novos); compileall, diff-check: PASS.

### WP-161 — Resumo de próximas ações no dashboard

O dashboard mostrava contagens mas não destacava o que precisa atenção imediata.
Adicionado `next_actions` ao endpoint /internal-tasks/dashboard derivando itens
pendentes: oportunidades sem triagem, conversas abertas, leads novos, tarefas
falhadas e review queue pendente. Seção visual "⚡ Próximas ações" no dashboard.
**2138 testes passaram** (9 novos); compileall, diff-check: PASS.

### WP-163 — Toggle de tema claro/escuro no operador

O painel do operador tinha apenas tema escuro. Adicionado botão de alternância
de tema (🌙/☀️) na barra superior com persistência em localStorage.
CSS com [data-theme="light"] override de todas as variáveis customizadas.
**2158 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-164 — Botão "Limpar filtros" na seção de tarefas internas

A seção de tarefas internas tinha filtros (status, data, ordenação) mas sem
botão para limpar todos de uma vez. Adicionado botão "Limpar filtros" seguindo
o padrão dos outros módulos.
**2168 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-165 — Botão "Limpar filtros" em leads e customers

Os módulos de leads e customers tinham filtros (status, busca, data, ordenação)
mas sem botão para limpar todos de uma vez. Adicionado botão "Limpar filtros"
completando a paridade com os outros 4 módulos. Export CSV de leads movido para
a barra de filtros para consistência visual.
**2191 testes passaram** (23 novos); compileall, diff-check: PASS.

### WP-166 — Atualizar README com estado atual do projeto

README atualizado com 2191 testes e lista completa de funcionalidades:
paridade de filtros em todos os 6 módulos, tema claro/escuro, notas em
conversas, bulk operations, exportação CSV completa e filtros de data.

### WP-167 — Criar oportunidade a partir de customer

O painel de detalhes do customer não tinha botão para criar uma nova
oportunidade vinculada ao customer. Adicionado formulário inline com
título, descrição, orçamento, prazo e requisitos. A oportunidade é
criada via POST /opportunities com source "manual" e external_url
referenciando o customer.

**2212 testes passaram** (21 novos); compileall, diff-check: PASS.

### WP-168 — Mais atalhos de teclado no operador

Além de Ctrl+K e Escape, adicionados: Ctrl+N (novo lead), Ctrl+L
(busca leads), Ctrl+Shift+C (busca customers) e / (busca
oportunidades). Rodapé atualizado com lista completa de atalhos.

**2226 testes passaram** (14 novos); compileall, diff-check: PASS.

### WP-169/170 — Exclusão em massa de customers e leads

O operador não podia excluir múltiplos customers ou leads de uma vez.
Adicionado `POST /customers/bulk-delete` e `POST /leads/bulk-delete`,
tenant-isolados, com 1-100 IDs. UI com checkboxes em cada item e barra
de ação em massa com contador, botão excluir e botão limpar seleção.

**2241 testes passaram** (15 novos); compileall, diff-check: PASS.

### WP-171 — Decisão em massa na review queue

O operador só podia aprovar/rejeitar um item de cada vez na review queue.
Adicionado `POST /review-queue/bulk-decision`, tenant-isolado, com 1-100 IDs.
UI com checkboxes em cada item e barra de ação em massa com contador,
botão aprovar, botão rejeitar e botão limpar seleção.

**2253 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-172 — Retry em massa das tarefas internas

O operador só podia retryar uma tarefa de cada vez.
Adicionado `POST /internal-tasks/bulk-retry`, tenant-isolado, com 1-100 IDs.
UI com checkboxes em cada tarefa e barra de ação em massa com contador,
botão retry e botão limpar seleção.

**2262 testes passaram** (9 novos); compileall, diff-check: PASS.

### WP-174 — Edição parcial do proposal brief

O schema ProposalBriefUpdate exigia todos os campos obrigatórios,
impossibilitando edições parciais. Todos os campos tornados opcionais;
endpoint PATCH usa model_dump(exclude_unset=True) para atualizar
apenas os campos fornecidos.

**2272 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-175 — Badges visuais em leads e conversas

O operador tinha badge apenas nas oportunidades pendentes.
Adicionado badge vermelho ao lado de "Leads" (contagem de leads novos)
e "Conversas" (contagem de conversas abertas).
Polling de notificações atualiza os 3 badges em paralelo.

**2272 testes passaram**; compileall, diff-check: PASS.

### WP-176 — Criar conversa a partir de lead

O operador podia criar conversas a partir de customers (WP-089),
mas não de leads. Adicionado botão "+ Nova conversa" no painel de
detalhes do lead. A conversa é criada via POST /conversations com
lead_id vinculado, seguindo o padrão da WP-089.

**2288 testes passaram** (16 novos); compileall, diff-check: PASS.

### WP-177 — Filtro de leads por fonte (source)

O módulo de leads tinha filtro por status, mas não por fonte.
Adicionado `?source=` em list, count e export CSV.
UI com dropdown "Fonte" (manual, 99freelas, intake, review_queue, import).

**2304 testes passaram** (16 novos); compileall, diff-check: PASS.

### WP-178 — Lista consolidada de proposal briefs

O operador só via o brief da oportunidade selecionada.
Adicionado `GET /proposal-briefs` e `GET /proposal-briefs/count`
com tenant isolation via JOIN Opportunity → Company.
UI com seção "11 / BRIEFS" mostrando título, referência, status e data.

**2314 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-180 — Exclusão em massa de oportunidades e conversas

Oportunidades e conversas não tinham exclusão em massa.
Adicionado `POST /opportunities/bulk-delete` e `POST /conversations/bulk-delete`,
tenant-isolados, seguindo o padrão de leads/customers.

**2322 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-181 — Busca, ordenação e paginação de briefs

O módulo de briefs tinha filtro por status mas não tinha busca, ordenação
nem paginação. Adicionado `?q=`, `?sort=`, `?limit=`, `?offset=` nos
endpoints list e count, completando a paridade com os outros módulos.

**2335 testes passaram** (13 novos); compileall, diff-check: PASS.

### WP-182 — Exportação CSV de briefs

O módulo de briefs não tinha exportação CSV. Adicionado
`GET /proposal-briefs/export.csv` com filtros (status, busca),
completando a paridade com os outros módulos.

**2341 testes passaram** (6 novos); compileall, diff-check: PASS.

### WP-183 — Filtro de data em briefs

O módulo de briefs não tinha filtro por data. Adicionado \`from_date\`/ \`to_date\`
em list, count e export CSV, completando a paridade com os outros módulos.

**2347 testes passaram** (6 novos); compileall, diff-check: PASS.

### WP-184 — Status em massa de proposal briefs

O operador só podia atualizar o status de um brief de cada vez.
Adicionado `POST /proposal-briefs/bulk-status` tenant-isolado com 1-100 IDs.
UI com checkboxes e barra de ação em massa.

**2355 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-185 — Exclusão em massa de proposal briefs

O operador não podia excluir múltiplos briefs de uma vez.
Adicionado `POST /proposal-briefs/bulk-delete` tenant-isolado com 1-100 IDs.
Botão "Excluir selecionados" na barra bulk existente.

**2361 testes passaram** (6 novos); compileall, diff-check: PASS.

### WP-187 — Detalhes expandidos do proposal brief

O operador via apenas título, referência e status na lista de briefs.
Adicionado `GET /proposal-briefs/{id}` retornando todos os campos (diagnóstico,
escopo, entregáveis, critérios de aceitação). Painel clicável na UI.

**2366 testes passaram** (5 novos); compileall, diff-check: PASS.

### WP-188 — Conversas relacionadas ao proposal brief

O painel de detalhes do brief não mostrava o contexto de conversas.
Adicionado `GET /proposal-briefs/{id}/conversations` retornando as conversas
da mesma company. UI carrega conversas em paralelo com os dados do brief.

**2371 testes passaram** (5 novos); compileall, diff-check: PASS.

### WP-189 — Filtro de oportunidades por fonte

O módulo de oportunidades não tinha filtro por fonte (source).
Adicionado `?source=` em list, count e export CSV.
UI com dropdown "Fonte" na toolbar.

**2377 testes passaram** (6 novos); compileall, diff-check: PASS.

### WP-190 — Botão limpar intake e labels de fonte

O formulário de intake comercial não tinha botão para limpar após envio,
e a fonte da oportunidade era exibida em inglês.
Adicionado botão "Limpar" que reseta formulário e esconde decisão.
Adicionado `sourceLabels` para exibir fonte em português.

**2387 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-191 — Corrigir filtro de fonte das oportunidades

O dropdown de filtro de fonte não incluía "99freelas", que é uma fonte
válida usada no sistema. Adicionado ao dropdown e atualizado README.

**2387 testes passaram**; compileall, diff-check: PASS.

### WP-192 — Criar oportunidade a partir de lead detail

O painel de detalhes do lead não tinha botão para criar oportunidade,
enquanto o customer detail já tinha (WP-167). Adicionado formulário inline
seguindo o mesmo padrão: título, descrição, orçamento, prazo, requisitos.

**2402 testes passaram** (15 novos); compileall, diff-check: PASS.

### WP-193 — Próximas ações clicáveis no dashboard

O dashboard mostrava as próximas ações mas não era possível clicar
para navegar até a seção relevante. Adicionado scroll suave ao clicar
em cada item, com tooltip e feedback visual (hover).

**2412 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-195 — Filtro de conversas por customer na UI

O backend de conversas já suportava `?customer_id=` (list, count, export),
mas a UI não expunha essa funcionalidade. Adicionado dropdown "Customer"
na seção de filtros que carrega os customers e filtra as conversas.

**2425 testes passaram** (13 novos); compileall, diff-check: PASS.

### WP-196 — Handler de exportação CSV de conversas

O botão "Exportar CSV" existia no HTML mas não tinha handler JavaScript.
Conectado ao endpoint existente, respeitando todos os filtros ativos
(channel, status, busca, customer_id, datas).

**2435 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-198 — Fontes de oportunidade no dashboard

O dashboard mostrava contagens por status mas não de onde vêm as
oportunidades. Adicionado `opportunities_by_source` ao endpoint
`/internal-tasks/dashboard` e seção visual "📊 Fontes de oportunidade"
no dashboard do operador.

**2444 testes passaram** (9 novos); compileall, diff-check: PASS.

### WP-199 — Fontes de lead no dashboard

Mesmo padrão da WP-198 aplicado aos leads: `leads_by_source` no
endpoint `/internal-tasks/dashboard` e seção visual "📊 Fontes de lead"
no dashboard do operador.

**2449 testes passaram** (5 novos); compileall, diff-check: PASS.

### WP-202 — System prompt configurável no agente

O agente de IA usava um prompt fixo. Agora `generate_agent_reply()`
aceita `system_prompt` opcional, permitindo sobrescrever o prompt
padrão. `AgentRequest` schema com `system_prompt` opcional. O endpoint
`POST /agent-reply` passa o prompt customizado. Preparação para
configuração por Company (F3) sem migration.

**2459 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-203 — Temperatura configurável no agente

O agente de IA usava temperatura fixa do modelo. Agora `generate_agent_reply()`
aceita `temperature` opcional (float 0.0-2.0), passando para o Ollama via
`options` dict. `AgentRequest` schema com `temperature` opcional. O endpoint
`POST /agent-reply` passa a temperatura. Complementa o system_prompt (WP-202)
preparando para configuração por Company (F3) sem migration.

**2489 testes passaram** (15 novos); compileall, diff-check: PASS.

### WP-204 — Configuração de agente por Company

Cada Company pode agora configurar seu próprio system_prompt e temperatura
para o agente de IA. Configuração armazenada em memória (sem migration).
`CompanyAgentConfig` schema; endpoints GET/PUT `/companies/{id}/agent-config`
com tenant isolation. O `POST /agent-reply` usa a config da company como
padrão, com parâmetros explícitos da requisição tendo precedência.

**2509 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-205 — Interface de configuração do agente no operador

O operador não podia visualizar ou editar as configurações do agente
(system_prompt, temperature) configuradas por Company (WP-204).
Seção "12 / AGENTE IA" com campos de prompt e temperatura, botão salvar
com feedback visual. `loadAgentConfig()` carrega ao conectar.

**2529 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-207 — Validação de temperatura do agente

O agente aceitava qualquer valor de temperatura sem validação.
`AgentRequest` e `CompanyAgentConfig` agora validam que temperature
está entre 0.0 e 2.0. Valores fora desse intervalo são rejeitados no
nível do schema, impedindo valores inválidos de chegarem à API do Ollama.

**2558 testes passaram** (29 novos); compileall, diff-check: PASS.

### WP-208 — Max tokens configurável no agente

O agente não tinha limite de tokens configurável. `generate_agent_reply()`
aceita `max_tokens` opcional (int >= 1), passando para o Ollama via
`num_predict` no options dict. `AgentRequest` e `CompanyAgentConfig` com
`max_tokens` opcional e validação. O endpoint `POST /agent-reply` passa
o max_tokens. Complementa system_prompt (WP-202) e temperature (WP-203).

**2591 testes passaram** (33 novos); compileall, diff-check: PASS.

### WP-210 — Campo max_tokens na configuração do agente UI

A interface de configuração do agente tinha campos de prompt e temperatura
mas faltava max_tokens (adicionado no backend pela WP-208). Adicionado
campo de entrada numérico com validação min=1.

**2611 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-211 — Botão "Voltar" e título no painel de detalhes do brief

O painel de detalhes do brief (WP-187) não tinha botão para voltar à lista
nem título visível. Adicionado cabeçalho com botão "← Voltar" e título
dinâmico baseado na oportunidade.

**2630 testes passaram** (19 novos); compileall, diff-check: PASS.

### WP-212 — Atualizar README

README atualizado com 2630 testes e novas funcionalidades:
campo max_tokens na UI do agente e painel de detalhes do brief
com botão "Voltar" e título dinâmico.

**2630 testes passaram**; compileall, diff-check: PASS.

### WP-213 — Seleção de modelo por company

O modelo do Ollama estava fixo como `qwen3:8b` para todas as companies.
Agora cada company configura seu próprio modelo via agent config.

**2662 testes passaram** (31 novos: 15 WP-213 + 16 WP-214); compileall, diff-check: PASS.

### WP-214 — Seletor de modelo na UI do agente

A interface de configuração do agente tinha prompt, temperatura e max_tokens
mas faltava o seletor de modelo. Adicionado dropdown com modelos comuns
do Ollama (qwen3:8b, qwen2.5:7b, llama3.1:8b, mistral:7b, gemma2:9b).

**2662 testes passaram**; compileall, diff-check: PASS.

### WP-215 — Atualizar README

README atualizado com 2662 testes e novas funcionalidades:
seleção de modelo por company e seletor de modelo na UI do agente.

**2662 testes passaram**; compileall, diff-check: PASS.

### WP-216 — Rastreamento de uso do agente

Para observabilidade F3, é necessário saber quantas chamadas ao agente
foram feitas por company e quantas falharam. Adicionado rastreamento
in-memory de chamadas bem-sucedidas e falhas, com endpoint de consulta.

**2676 testes passaram** (14 novos); compileall, diff-check: PASS.

### WP-217 — Métricas do agente no dashboard

O dashboard do operador não mostrava o uso do agente IA. Adicionado
card "🤖 Agente IA" com contagem total de chamadas, sucesso e falha,
alimentado pelo endpoint /dashboard que agora inclui agent_usage.

**2686 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-218 — Atualizar README

README atualizado com 2686 testes e novas funcionalidades:
rastreamento de uso do agente e métricas no dashboard.

**2686 testes passaram**; compileall, diff-check: PASS.

### WP-219 — Validação de modelo no agente

O schema aceitava qualquer string para `model`. Adicionado validador
`model_not_empty` em `CompanyAgentConfig` e `AgentRequest` que rejeita
strings vazias, apenas espaços e nomes com mais de 100 caracteres.

**2705 testes passaram** (16 novos); compileall, diff-check: PASS.

### WP-220 — Fallback de modelo quando não existe no Ollama

Quando uma company configura um modelo que não existe no servidor Ollama,
o agente faz fallback para o modelo padrão (`settings.ollama_model`) em vez
de falhar. O fallback ocorre apenas uma vez; se o modelo padrão também falhar,
o erro é propagado normalmente.

**2712 testes passaram** (7 novos); compileall, diff-check: PASS.

### WP-221 — Endpoint de modelos disponíveis

`GET /agent-models-available` retorna lista estática de modelos Ollama
configuráveis (qwen3:8b, qwen2.5:7b, llama3.1:8b, mistral:7b, gemma2:9b)
com marcação do modelo padrão. Sem autenticação, útil para o dropdown da UI.

**2719 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-223 — Atividades recentes no dashboard

O dashboard mostrava contagens agregadas mas não o que aconteceu recentemente.
`GET /internal-tasks/recent-activities` retorna as atividades mais recentes
(oportunidades, conversas, leads) ordenadas por data, com filtro por tipo
e tenant isolation. Limit configurável (default 20, max 100).

**2731 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-224 — Busca por keywords na review queue

A review queue tinha filtro por status, ordenação, paginação e filtro de data,
mas não tinha busca por keywords. Adicionado `?q=` em list, count e export CSV
com busca case-insensitive em message, intent e event_id. UI com campo de busca
na seção de filtros, listener de input para busca em tempo real.

**2750 testes passaram** (19 novos: 9 backend + 10 UI); compileall, diff-check: PASS.

### WP-225 — Busca por keywords nas tarefas internas

O módulo de tarefas internas tinha filtro por status, ordenação, paginação e filtro
de data, mas não tinha busca por keywords. Adicionado `?q=` em list, count e export CSV
com busca case-insensitive em event_id e error_code. UI com campo de busca na seção
de filtros, listener de input para busca em tempo real; botão "Limpar filtros" atualizado.

**2759 testes passaram** (9 novos); compileall, diff-check: PASS.

### WP-226 — Sugerir resposta do agente sem persistir

O operador podia disparar agent-reply mas precisava digitar uma mensagem do cliente.
`POST /conversations/{id}/suggest-reply` usa a última mensagem do cliente na conversa
e retorna uma sugestão do agente sem persisti-la. Usa a configuração do agente da
company (prompt, temperatura, tokens, modelo). Retorna 400 se não houver mensagem
do cliente; 503 se o agente falhar.

**2767 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-227 — Botão "Sugerir resposta" na UI de conversas

O endpoint suggest-reply (WP-226) não tinha interface visual. Adicionado botão
"🤖 Sugerir resposta" no painel de detalhes da conversa. Ao clicar, solicita
ao agente uma sugestão baseada na última mensagem do cliente. Exibe a sugestão
em painel dedicado com botão "Copiar" que preenche o formulário de resposta
manual. Tratamento de 400 (sem mensagem cliente) e 503 (agente indisponível).

**2767 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-230 — Exclusão em massa da review queue

A review queue tinha bulk approve/reject mas não tinha bulk delete, impedindo
a limpeza em massa dos itens já decididos. `POST /review-queue/bulk-delete`
tenant-isolado com 1-100 IDs. Botão "Excluir selecionados" na barra de ações
em massa com confirmação via `confirm()`.

**2787 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-232 — Filtro de conversas por lead

O módulo de conversas tinha filtro por `customer_id` mas não por `lead_id`.
Adicionado `?lead_id=` em list, count e export CSV. Dropdown "Lead" na UI
populado dinamicamente a partir dos leads da company.

**2795 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-233 — Filtro de briefs por opportunity

O módulo de briefs tinha filtro por status mas não por `opportunity_id`.
Adicionado `?opportunity_id=` em list, count e export CSV. Isolamento tenant
via JOIN com Opportunity.

**2802 testes passaram** (7 novos); compileall, diff-check: PASS.

### WP-234 — Filtro de briefs por oportunidade na UI

O backend de briefs suporta `?opportunity_id=` (WP-233) mas a UI não tinha
dropdown correspondente. Adicionado seletor "Oportunidade" que carrega as
oportunidades da company e filtra a lista, count e export CSV.

**2802 testes passaram**; compileall, diff-check: PASS.

### WP-235 — Criar customer a partir de conversa

O operador podia criar leads a partir de conversas (WP-147) mas não customers.
Adicionado botão "+ Criar customer desta conversa" no painel de detalhes da
conversa, com formulário inline (nome, telefone, e-mail, fonte). A fonte é
pré-preenchida com o canal da conversa. Handler de submit via customerApi
com POST /customers; allowlist atualizado.

**2822 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-236 — Criar oportunidade a partir de conversa

O operador podia criar leads (WP-147) e customers (WP-235) a partir de conversas
mas não oportunidades. Adicionado botão "+ Criar oportunidade desta conversa"
no painel de detalhes da conversa, com formulário inline (título, descrição,
orçamento, prazo, requisitos). Source "manual". Handler de submit via api
com POST /opportunities; refreshList após sucesso.

**2842 testes passaram** (20 novos); compileall, diff-check: PASS.

### WP-237 — Sugestão de triagem por IA

`POST /opportunities/{id}/suggest-triage` analisa o contexto da oportunidade
(título, descrição, orçamento, prazo, requisitos, nota de triagem) e sugere
a próxima ação ideal. Usa config da company (prompt, temperatura, tokens,
modelo). Retorna 503 quando agente indisponível. UI com botão "🤖 Sugerir
triagem" e painel de resultado com "Aplicar sugestão" / "Descartar".

**2852 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-238 — Score de priorização automática de oportunidades

`_calculate_priority_score()` calcula score 0-100 baseado em deadline (0-40pts),
budget (0-20pts), status (0-25pts) e source (0-15pts). Novo endpoint
`GET /opportunities/priority` ordena por score. UI com opção "Ordenar:
Prioridade" e badges visuais (🔴 Alta, 🟡 Média, 🟢 Baixa).

**2864 testes passaram** (12 novos); compileall, diff-check: PASS.

### WP-239 — Oportunidades de prioridade alta no dashboard

O dashboard agora retorna `high_priority_opportunities` (top 5 com nível
"high", ordenadas por score descendente). Seção "🔴 Prioridade alta" entre
próximas ações e atividades recentes. Reusa `_calculate_priority_score`
de opportunities.py — sem migration.

**2872 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-240 — Sugestão de conteúdo do proposal brief por IA

`POST /opportunities/{id}/suggest-brief` analisa a oportunidade e sugere
diagnóstico, escopo, entregáveis e critérios. Schema `ProposalBriefSuggestion`
com offer_reference, diagnosis, scope, deliverables, acceptance_criteria,
assumptions, risks. Não persiste — o operador revisa e cria manualmente.
Segue o padrão WP-237: company config, 503 on error, fallback JSON.

**2882 testes passaram** (10 novos); compileall, diff-check: PASS.

### WP-241/242 — Interface de sugestão de brief por IA

Botão "🤖 Sugerir brief" no painel de detalhes da oportunidade, ao lado do
botão de sugestão de triagem. Painel de sugestão exibe os 7 campos do brief
usando textContent/appendChild (regra XSS). Botão "Preencher brief" auto-preenche
o formulário e rola até ele. Estado `briefSuggestion` resetado em clearSelection.
Allowlist atualizado para incluir `suggest-brief`.

**2909 testes passaram** (27 novos); compileall, diff-check: PASS.

### WP-246 — Export CSV com coluna de prioridade

O export CSV das oportunidades agora inclui o score de prioridade calculado
e o nível (high/medium/low), permitindo ao operador analisar as prioridades
em uma planilha. Reusa `_calculate_priority_score()` de WP-238.

**2921 testes passaram** (7 novos); compileall, diff-check: PASS.

### WP-247 — Sugestão de triagem em massa por IA

`POST /opportunities/bulk-suggest-triage` aceita 1-100 IDs e sugere a melhor
ação de triagem para o grupo, complementando WP-237 (sugestão individual)
e WP-105 (triagem em massa). Usa config da company (prompt, temperatura,
tokens, modelo). Retorna suggested_action, reasoning, matching_count e
total_count. Conta quantas oportunidades podem realmente transicionar para
a ação sugerida via `_VALID_TRANSITIONS`. Retorna 503 quando agente indisponível.

**2929 testes passaram** (8 novos); compileall, diff-check: PASS.

### WP-249 — Interface de sugestão de triagem em massa por IA

Botão "🤖 Sugerir ação" na barra de triagem em massa conecta ao backend
WP-247 (POST /opportunities/bulk-suggest-triage). Painel de sugestão exibe
ação sugerida, motivo e contagem de compatibilidade (N/total). Botão
"Aplicar sugestão" auto-preenche o seletor de ação; "Descartar" esconde.
Estado bulkTriageSuggestion resetado em clearSelection. Allowlist atualizado.

**2929 testes passaram**; compileall, diff-check: PASS.

### WP-250 — Export CSV détaillé des proposal briefs

L'export CSV des briefs inclut maintenant tous les champs détaillés:
diagnostic, scope, deliverables, critères d'acceptation, hypothèses et
risques — en plus des champs de base (ID, opportunité, titre, référence,
status, créée le). 12 colonnes au total. Respecte tous les filtres
existants (status, q, opportunity_id, from_date, to_date).

**2936 tests passés** (7 nouveaux); compileall, diff-check: PASS.

### WP-251 — Badge de notifications dans le titre du navigateur

Le titre de l'onglet affiche le compteur total de notifications:
pendentes + nouveaux leads + conversations ouvertes. "(N) Operador"
quand il y a des notifications, "Operador" sinon. Mise à jour automatique
à chaque polling de notifications (30s).

**2936 tests passés**; compileall, diff-check: PASS.

### WP-252 — Auto-suggestion IA quand on ouvre le formulaire de réponse

Quand l'opérateur clique sur "Responder" pour ouvrir le formulaire de
réponse manuelle, la suggestion IA se charge automatiquement via
POST /conversations/{id}/suggest-reply (WP-226). La suggestion est
insérée directement dans le champ de message. Les erreurs (400, 503)
sont silencieusement ignorées. Le bouton "🤖 Sugerir" reste disponible
pour recharger manuellement.

**2936 tests passés**; compileall, diff-check: PASS.

### WP-253 — Raccourcis clavier Ctrl+1 à Ctrl+7 pour naviguer entre les sections

L'opérateur peut naviguer entre les 7 sections avec Ctrl+1 (Dashboard),
Ctrl+2 (Oportunidades), Ctrl+3 (Conversas), Ctrl+4 (Leads),
Ctrl+5 (Customers), Ctrl+6 (Fila de revisão), Ctrl+7 (Tarefas internas).
Utilise scrollIntoView smooth, réutilisant la logique de WP-193.

**2936 tests passés**; compileall, diff-check: PASS.

### WP-254 — Mettre à jour le script de démonstration Client 0

Le script `scripts/demo_client0_cycle.sh` couvre maintenant le cycle F2
complet plus les fonctionnalités F3 récentes: exportation CSV, suggestion
de triage par IA, configuration de l'agent par Company, modèles disponibles
et activités récentes. 20 étapes au total.

**2936 tests passés**; bash syntax, compileall, diff-check: PASS.

### WP-256 — Métriques de performance commerciale dans le dashboard

Le dashboard inclut maintenant `performance_metrics` avec:
- `lead_conversion_rate`: % de leads convertis en customers
- `opportunity_closure_rate`: % d'opportunités fermées (done/lost/ignore)
- `brief_approval_rate`: % de briefs approuvés

Chaque métrique inclut le taux en pourcentage et le compteur brut.
7 tests backend; tenant isolation et auth requis.

**2943 tests passés**; compileall, diff-check: PASS.

### WP-257 — Indicadores de performance no dashboard do operador

Seção "Indicadores de performance" com 3 cards: taxa de conversão
(leads), taxa de fechamento (oportunidades), taxa de aprovação (briefs).
Cada card mostra a porcentagem e o contador bruto.

Correção: removida sintaxe TypeScript inválida em app.js.

**2943 tests passed**; JS syntax, compileall, diff-check: PASS.

### WP-258 — Sugestão IA para intake comercial

Novo endpoint `POST /internal/commercial-intake/suggest` que usa o agente
IA (Ollama) para prever intenção e categoria antes da submissão. O operador
pode validar ou corrigir antes de criar a oportunidade. Usa config da company
(prompt, temperatura, tokens, modelo). 503 quando agente indisponível.

**2953 tests passed**; compileall, diff-check: PASS.

### WP-259 — Interface UI para sugestão IA de intake

Botão "🤖 Sugerir" no formulário de intake comercial chama o endpoint
/suggest e mostra a previsão da IA (intenção, categoria, raciocínio)
antes da criação da oportunidade. Tratamento de erro 503.

**2953 tests passed**; JS syntax, compileall, diff-check: PASS.

### WP-260 — Raccourcis clavier étendus et correction du store agent

Ajouté Ctrl+8 (Briefs), Ctrl+9 (Intake) et Ctrl+0 (Agent) pour la
navigation entre toutes les sections du panneau opérateur. Corrigé la
duplication de _agent_config_store dans commercial_intake.py.

**2953 tests passed**; compileall, diff-check, JS syntax: PASS.

### WP-261 — Ordenação de leads por nome

Adicionado `sort=name` ao backend de leads e opção "Nome" ao dropdown
de ordenação na UI do operador. Completou a paridade com customers.

**2959 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-262 — Ordenação de briefs por título da oportunidade

Adicionado `sort=title` ao backend de briefs e opção "Título" ao dropdown
de ordenação na UI do operador.

**2965 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-263 — Filtro de oportunidades por lead e customer

Adicionado `lead_id` e `customer_id` em list, count e export CSV das
oportunidades usando EXISTS subquery com Conversation. UI com dropdowns
"Lead" e "Customer" na toolbar.

**2978 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-264 — Templates de resposta reutilizáveis

O operador pode salvar respostas comuns e reusá-las rapidamente ao
responder conversas. Backend com GET/POST/DELETE /companies/{id}/reply-templates
com tenant isolation e armazenamento em memória. UI com seletor de templates
no formulário de resposta.

**2992 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-265 — Interface de gerenciamento de templates de resposta

O operador podia selecionar templates nas respostas (WP-264) mas não
tinha forma de criá-los ou gerenciá-los. Adicionada subseção
"Templates de resposta" na seção "12 / AGENTE IA" com formulário de
criação, lista de templates existentes com botão excluir.

**3007 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-266 — Filtro por nível de prioridade nas oportunidades

O score de prioridade já era calculado (WP-238) mas não dava para
filtrar. Adicionado `?priority_level=` em list, count e export CSV.
Dropdown "Prioridade" na UI com opções Alta, Média e Baixa.

**3017 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-267 — Sugestão IA para criar lead a partir de conversa

O operador podia criar leads manualmente a partir de conversas mas
não tinha ajuda da IA. Adicionado `POST /conversations/{id}/suggest-lead`
que analisa as mensagens e sugere nome, telefone e interesse.

UI: botão "🤖 Sugerir" no formulário de criar lead; painel mostra
razão; "Preencher lead" auto-preenche os campos. Segue regra XSS.

**3027 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-268 — Sugestão IA para criar customer a partir de conversa

O operador podia criar customers manualmente a partir de conversas mas
não tinha ajuda da IA. Adicionado `POST /conversations/{id}/suggest-customer`
que analisa as mensagens e sugere nome, telefone e e-mail.

UI: botão "🤖 Sugerir" no formulário de criar customer; painel mostra
razão; "Preencher customer" auto-preenche os campos. Segue regra XSS.

**3036 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-269 — Sugestão IA para criar oportunidade a partir de conversa

O operador podia criar oportunidades manualmente a partir de conversas mas
não tinha ajuda da IA. Adicionado `POST /conversations/{id}/suggest-opportunity`
que analisa as mensagens e sugere título, descrição, orçamento, prazo e
requisitos.

UI: botão "🤖 Sugerir" no formulário de criar oportunidade; painel mostra
razão; "Preencher oportunidade" auto-preenche os campos. Segue regra XSS.

**3045 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-270 — Resumo de conversa por IA

O operador podia ver todas as mensagens mas não tinha forma rápida
de resumir conversas longas. Adicionado `POST /conversations/{id}/summarize`
que analisa todas as mensagens e retorna resumo conciso com pontos-chave
e ações pendentes. Usa config da company. Mínimo 2 mensagens.

UI: botão "📋 Resumir" no painel de detalhes; painel mostra resumo,
pontos-chave e ações pendentes. Segue regra XSS.

**3055 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-271 — Sugestão IA para criar oportunidade a partir de lead

O operador podia criar oportunidades manualmente a partir do lead
mas não tinha ajuda da IA. Adicionado `POST /leads/{id}/suggest-opportunity`
que analisa nome, interesse, fonte e status do lead para sugerir
título, descrição, orçamento, prazo e requisitos. Usa config da company.

UI: botão "🤖 Sugerir" no formulário de oportunidade do lead detail;
painel mostra sugestão com botão "Preencher formulário".

**3064 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-272 — Sugestão IA para criar oportunidade a partir de customer

O operador podia criar oportunidades manualmente a partir do customer
mas não tinha ajuda da IA. Adicionado `POST /customers/{id}/suggest-opportunity`
que analisa nome, telefone, e-mail e origem do customer para sugerir
título, descrição, orçamento, prazo e requisitos. Usa config da company.

UI: botão "🤖 Sugerir" no formulário de oportunidade do customer detail;
painel mostra sugestão com botão "Preencher formulário".

**3073 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-273 — Sugestão IA para criar lead a partir de customer

O operador podia criar oportunidades de customer (WP-272) mas não
leads com ajuda da IA. Adicionado `POST /customers/{id}/suggest-lead`
que analisa nome, telefone, e-mail e origem do customer para sugerir
nome, telefone e interesse do lead. Usa config da company.

UI: seção "Leads" no customer detail com formulário de criação e
botão "🤖 Sugerir" com painel de sugestão.

**3082 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-274 — Sugestão IA para mensagem inicial de conversa

O operador criava conversas sem ajuda da IA para a primeira mensagem.
Adicionado `POST /conversations/suggest-message` que analisa o contexto
do lead ou customer e sugere mensagem de abertura personalizada.

UI: formulários de nova conversa nos painéis de detalhes de lead e
customer com canal, mensagem e botão "🤖 Sugerir".

**3092 testes passaram**; compileall, diff-check, JS syntax: PASS.

### WP-278 — Ownership de contato em oportunidades

Oportunidades passaram a aceitar um Lead ou Customer explícito do mesmo tenant,
com FKs, índices e constraint de exclusão mútua. A UI cria/sugere conversas
somente para o contato vinculado e invalida respostas assíncronas antigas.

PR #291 integrado em `d96f76d`. Migration `f278a1b2c3d4` foi validada somente
no PostgreSQL descartável; nenhuma migration real foi executada.

### WP-279 — Conversas de oportunidades vinculadas a Customers

O painel passou a tratar Customer e Lead de forma equivalente, usando
`customer_id` ou `lead_id` conforme o vínculo explícito. PR #292 integrado em
`9d00838`; não houve alteração de schema adicional.

### WP-280 — Conversas realmente relacionadas à oportunidade

Adicionada `/opportunities/{id}/linked-conversations`, filtrada pelo contato
vinculado e pela Company autenticada. O endpoint legado permanece compatível;
somente o painel usa a rota vinculada. PR #293 integrado em `8cda491`.

Estado atual: suíte local em **3141 testes**, dois warnings preexistentes;
compileall, sintaxe JavaScript e diff-check passam. O próximo recorte pode
tratar observabilidade ou filtros operacionais, mantendo o gate de não enviar
mensagens externas e sem ativar n8n.

### WP-282 — Ownership Customer preservado na UI

O formulário de criação de oportunidade aberto no detalhe de Customer agora
envia `customer_id`, preservando o vínculo explícito necessário ao fluxo de
conversas das WPs 279 e 280. PR #295 integrado em `14288ae`.

Validação local e CI: **3141 testes passaram**, dois warnings preexistentes;
compileall, sintaxe JavaScript e diff-check: PASS. Nenhuma migration nova ou
alteração de backend foi necessária.

### WP-287 — Navegação acessível para Leads vinculados

Cards de Lead no detalhe de oportunidade agora abrem diretamente o detalhe do
Lead e aceitam ativação por teclado, mantendo paridade com Customer. PR #300
integrado em `89ba564`.

Validação local e CI: **3142 testes passaram**, dois warnings preexistentes;
compileall e diff-check: PASS. Nenhuma migration ou alteração de API foi
necessária.

### WP-294 — Semântica de itens nas listas vinculadas

Os cards dinâmicos de conversas, Leads e Customers vinculados agora usam
`role="listitem"`, completando a semântica das listas anunciadas pela WP-293.
PR #307 integrado em `bcbaef9`.

Validação local e CI: **3143 testes passaram**, dois warnings preexistentes;
compileall e diff-check: PASS.

### WP-299 — Estado busy das listas vinculadas

As listas de conversas, Leads e Customers vinculados agora expõem `aria-busy`
durante a atualização e removem o estado ao concluir. PR #312 integrado após
CI verde.

Validação local e CI: **3144 testes passaram**, dois warnings preexistentes;
compileall e diff-check: PASS.

### WP-301 — Estado inicial busy das listas

As listas vinculadas agora declaram explicitamente `aria-busy="false"` no
HTML inicial, evitando estado indeterminado antes da primeira seleção.
PR #314 integrado após CI verde.

Validação: 6 testes direcionados, compileall e diff-check passaram.

### WP-363 — Estado inicial busy de Proposal Briefs

A lista de Proposal Briefs agora declara `aria-busy="false"` no HTML inicial,
evitando estado indeterminado antes da primeira atualização. PR #376 integrado
após CI verde.

Validação: 59 testes direcionados, compileall e diff-check passaram.

### WP-307 — Nota de triagem anunciada

A nota de triagem da oportunidade selecionada agora usa `aria-live="polite"`,
anunciando atualizações para leitores de tela. PR #320 integrado após CI verde.

Validação: 7 testes direcionados, compileall e diff-check passaram.

### WP-303 — Anúncio da oportunidade selecionada

O identificador da oportunidade selecionada agora usa `aria-live="polite"`,
anunciando mudanças de seleção para leitores de tela. PR #316 integrado após
CI verde.

Validação: 5 testes direcionados, compileall e diff-check passaram.

### WP-305 — Status de ProposalBrief anunciado

O status dinâmico do ProposalBrief agora usa `aria-live="polite"`, informando
leitores de tela sobre mudanças no detalhe da oportunidade. PR #318 integrado.

Validação: 6 testes direcionados, compileall e diff-check passaram.

### WP-289 — Foco visual para contatos vinculados

Cards de Lead e Customer vinculados a oportunidades agora exibem foco visível
ao navegar por teclado, complementando a ativação acessível das WPs 286 e 287.
PR #302 integrado em `f801bf3`.

Validação: testes específicos, compileall e diff-check passaram; nenhuma
alteração de API, schema ou migration foi necessária.

### WP-284 — Contexto de Customer no detalhe de oportunidade

O cartão de Customer vinculado a uma oportunidade agora exibe telefone e
status quando disponíveis, usando a linguagem do operador (`Cliente`) e
mantendo paridade contextual com Lead. PR #297 integrado em `f402e48`.

Validação local e CI: **3142 testes passaram**, dois warnings preexistentes;
compileall e diff-check: PASS. Nenhuma migration ou alteração de API foi
necessária.

## WP-385 — Aliases padronizados de health probes (05/11/2026)

Adicionados os aliases públicos `/healthz` e `/readyz`, preservando os
contratos existentes de `/health` e `/readiness`. Os quatro endpoints mantêm
respostas sem autenticação e sem detalhes de infraestrutura.

Validação local: **3205 testes passaram**, `compileall app tests` e
`git diff --check` passaram. PR #385 foi integrado após CI verde no commit
`058dcb8`. Não houve migration, acesso a banco real, deploy ou ação externa.

## WP-386 — Health probes sem cache (05/11/2026)

Os quatro endpoints de liveness/readiness agora retornam
`Cache-Control: no-store`, evitando que proxies ou supervisores reutilizem um
estado de saúde obsoleto. O corpo e os códigos HTTP existentes foram
preservados, com testes de regressão para cada alias.

Validação local: **3205 testes passaram**, `compileall app tests` e
`git diff --check` passaram. PR #386 foi integrado após CI verde no commit
`2f6960b`. O arquivo local não rastreado `error.log` permaneceu fora do Git.

Próxima ação segura: escolher uma fatia funcional do operador ou uma lacuna
de diagnóstico comprovada no código, evitando novas alterações cosméticas de
acessibilidade enquanto houver fluxo operacional incompleto.

## WP-388 — Polling de notificações tenant-aware (05/11/2026)

O polling de notificações do operador deixou de consultar a Company `1` fixa
para contar conversas abertas. Agora o `company_id` é derivado dos dados de
oportunidades ou leads já retornados ao operador autenticado; sem dados de
tenant, nenhuma consulta de conversas é feita.

Validação local: **3206 testes passaram**, 61 testes direcionados do operador,
`node --check app/operator_ui/app.js`, `compileall app tests` e
`git diff --check` passaram. PR #388 foi integrado após CI verde no commit
`76e946e`. Nenhuma migration, mudança de autorização, mensagem externa ou
deploy foi executado.

## WP-390 — Contagens completas no polling de notificações (05/11/2026)

O polling de notificações do operador deixou de baixar listas de até 100 itens
para calcular badges. Ele usa os endpoints de contagem existentes para
oportunidades pendentes, leads novos, conversas abertas e tarefas falhas, e
consulta somente uma oportunidade/lead para descobrir o tenant autorizado.
Isso evita números truncados sem alterar os contratos de isolamento.

Validação local: **3207 testes passaram**, 87 testes direcionados, `node
--check app/operator_ui/app.js`, `compileall app tests` e `git diff --check`
passaram. Não houve migration, mudança de credencial, mensagem externa ou
deploy.

## WP-391 — Snapshot único para badges de notificações (05/11/2026)

O polling de notificações agora consulta uma única vez
`GET /internal-tasks/dashboard`, que já é autenticado e tenant-scoped. Os
badges de oportunidades pendentes, leads novos, conversas abertas e tarefas
falhas são derivados do mesmo snapshot, reduzindo cinco requisições e evitando
contagens observadas em momentos diferentes.

Validação local: **3207 testes passaram**, testes direcionados do operador e
do badge de tarefas passaram, `node --check app/operator_ui/app.js`,
`compileall app tests` e `git diff --check` passaram. Nenhuma migration,
credencial, mensagem externa ou deploy foi envolvido.

## WP-392 — Estado visível de sincronização de notificações (05/11/2026)

O painel do operador agora informa quando o snapshot de notificações foi
atualizado e quando a atualização está indisponível. Em caso de falha, os
badges não são apresentados como novos dados; o estado permanece explícito
para o operador sem expor detalhes internos.

Validação local: **3208 testes passaram**, 78 testes direcionados do operador,
`node --check app/operator_ui/app.js`, `compileall app tests` e
`git diff --check` passaram. Nenhuma migration, credencial, mensagem externa
ou deploy foi envolvido.

## WP-393 — Endpoint leve para resumo de notificações (05/11/2026)

Criado `GET /internal-tasks/notification-summary`, autenticado e filtrado
pela Company do operador, retornando somente os quatro contadores usados pelos
badges. O polling deixou de executar o dashboard completo para uma atualização
de fundo, reduzindo trabalho de banco e preservando isolamento entre tenants.

Validação local: **3211 testes passaram**, 87 testes direcionados, `node
--check app/operator_ui/app.js`, `compileall app tests` e `git diff --check`
passaram. Nenhuma migration, credencial, mensagem externa ou deploy foi
envolvido.

## WP-394 — Esteira local contínua do Codex (05/11/2026)

Adicionados `scripts/continuous-dev-loop.sh` e
`scripts/continuous-dev-task.md`. O supervisor executa uma WP por invocação,
preserva logs fora do Git, recusa árvore suja e PRs abertos antes da execução,
respeita `/tmp/business-automation.stop` e usa backoff para falhas transitórias.
O PR #394 foi integrado no commit `f48438b` após CI verde.

## WP-395 — Merge seguro após CI do PR do Codex (05/11/2026)

O supervisor agora exige exatamente um PR `wp/*` após a execução, captura o
head SHA, aguarda o `statusCheckRollup` via GitHub CLI com polling interrompível,
recusa CI pending/falho, head alterado, revisão humana e escopos protegidos,
faz merge normal de WPs seguras e sincroniza `main` antes de retornar sucesso.
Falhas terminais não entram no backoff automático nem iniciam outra WP.
Fixtures locais validaram PR inexistente, PR único verde, CI pending com
stop-file, CI falho, múltiplos PRs, revisão obrigatória, árvore suja e branch
fora da `main`.

## WP-396 — Compatibilidade do Codex com hooks locais (05/11/2026)

O launcher usa `--ignore-user-config` porque os hooks globais do
`context-mode` falharam com `NODE_TOO_OLD` dentro do Codex filho. A flag foi
validada com smoke test read-only e não desativa sandbox, approval policy,
`AGENTS.md`, guards do supervisor, CI ou revisão de escopos protegidos.

## Fatias funcionais completas

Cada novo ciclo deve entregar uma capacidade operacional vertical com backend/API,
fluxo de operador quando aplicável, testes e documentação. O PR só deve ser
aberto depois que essa fatia estiver completa e os gates locais passarem.

A sequência é sincronizar origin/main, ler produto/roadmap/decisões, escolher
uma capacidade do backlog, implementar em uma branch wp/<id>-<capacidade>,
executar scripts/preflight.sh, abrir um único PR, aguardar CI, fazer merge
normal quando verde e iniciar a próxima capacidade.

Não abrir PRs para microajustes isolados. Migrações, segurança, autorização,
isolamento tenant e infraestrutura continuam sujeitos aos gates adicionais de
AGENTS.md; nunca são habilitados por auto-merge.
