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
