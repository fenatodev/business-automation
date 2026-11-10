---
sessionId: session-261107-105944-690q
---

# Visão Geral

## Objetivo
Fechar as lacunas do projeto Business Automation para completar a **F2 (operação assistida)** e preparar a **F3 (automação)**, organizando o trabalho em **4 lotes sequenciais** de work packages.

## Estado Atual
- **F1 (fundação)**: ✅ Concluída — migrations, auth, tenant isolation, backup/restore
- **F2 (operação assistida)**: ✅ Concluída — ciclo comercial completo, UI do operador, exportação
- **F3 (automação)**: 🔄 Em progresso — base técnica pronta, automatizando gargalos

## Lotes
1. **Lote 1 — Ciclo comercial completo (F2)**: 8 WPs ✅ concluídas
2. **Lote 2 — UI/UX do operador**: 7 WPs (5 implementadas, 2 puladas) ✅ concluídas
3. **Lote 3 — Preparação F3 (automação)**: 6 WPs ✅ concluídas
4. **Lote 4 — Automação prática (F3)**: 6 WPs para automatizar gargalos comprovados

## Regras
- Cada WP é pequena, segura e funcional
- Sem n8n, deploy, dados reais, migrations ou auth/RBAC sem revisão humana
- Testes obrigatórios: `uv run pytest`, `compileall`, `git diff --check`
- Branch `wp/<id>-<descricao>`, commit convencional, PR único
- Merge só se CI verde, head SHA igual, sem revisão humana obrigatória

## Progresso
- **Lote 1**: 8/8 WPs merged (PRs #512-#517)
- **Lote 2**: 5/7 WPs merged (PRs #518-#522), 2 puladas (já cobertas)
- **Lote 3**: 6/6 WPs merged (PRs #523-#526)
- **Lote 4**: 0/6 WPs — em andamento
- **Testes totais**: 3519 passed, 2 warnings
- **Branch**: `main` sincronizada com `origin/main` (commit `ca52fc4`)

# Lote 1: Ciclo Comercial (F2)

## WP-512: Brief approve/reject com feedback
**Objetivo**: Permitir ao operador aprovar ou rejeitar um ProposalBrief com nota opcional.

- `app/routers/opportunities.py`: novo endpoint `PATCH /briefs/{id}/decision` com `status` (approved/rejected) e `operator_note`
- `app/models.py`: adicionar `operator_note` e `decided_at` a `ProposalBrief`
- `app/schemas.py`: schemas de request/response
- `app/operator_ui/app.js`: UI de decisão na seção Briefs com modal de approve/reject
- Testes: approve/reject flows, validation, tenant isolation

## WP-513: Opportunity close com motivo
**Objetivo**: Fechar uma oportunidade como won/lost com motivo e valor final.

- `app/routers/opportunities.py`: novo endpoint `PATCH /opportunities/{id}/close` com `outcome` (won/lost), `reason`, `final_value`
- `app/models.py`: adicionar `outcome`, `reason`, `final_value`, `closed_at` a `Opportunity`
- `app/schemas.py`: schemas de request/response
- `app/operator_ui/app.js`: UI de close na seção Carteira com seleção de motivo
- Testes: close flows, validation, status transitions

## WP-514: Lead → Customer conversion
**Objetivo**: Converter um Lead em Customer com histórico preservado.

- `app/routers/leads.py`: novo endpoint `POST /leads/{id}/convert` que cria Customer e vincula conversas
- `app/models.py`: garantir `Customer.lead_id` é populado corretamente
- `app/schemas.py`: schema de conversão
- `app/operator_ui/app.js`: botão de conversão na seção Leads com confirmação
- Testes: conversion flow, conversation linking, idempotency

## WP-515: Opportunity pipeline status transitions
**Objetivo**: Transitar uma oportunidade entre status do pipeline (new → qualified → proposal → negotiation → won/lost).

- `app/routers/opportunities.py`: novo endpoint `PATCH /opportunities/{id}/status` com validação de transições
- `app/services/commercial_pipeline.py`: definir máquina de estados e validações
- `app/schemas.py`: schema de transição
- `app/operator_ui/app.js`: dropdown de status com transições válidas na seção Carteira
- Testes: valid transitions, invalid transitions, status history

## WP-516: Conversation summary endpoint
**Objetivo**: Gerar resumo automático de uma conversa via IA para triagem rápida.

- `app/routers/conversations.py`: novo endpoint `POST /conversations/{id}/summarize`
- `app/services/agent.py`: método `summarize_conversation()` com fallback graceful
- `app/schemas.py`: schema de resumo
- `app/operator_ui/app.js`: botão de resumir na seção Conversas com loading state
- Testes: summary generation, agent failure handling, tenant isolation

## WP-517: Dashboard metrics por período
**Objetivo**: Permitir filtrar métricas do dashboard por período (7/30/90 dias).

- `app/routers/companies.py`: novo endpoint `GET /companies/{id}/metrics` com `period` query param
- `app/schemas.py`: schema de métricas
- `app/operator_ui/app.js`: seletor de período no dashboard com atualização de cards
- Testes: period filtering, metric calculation, edge cases

## WP-518: Exportação CSV de oportunidades
**Objetivo**: Exportar lista de oportunidades filtradas para CSV.

- `app/routers/opportunities.py`: novo endpoint `GET /opportunities/export` com filtros
- `app/schemas.py`: schema de exportação
- `app/operator_ui/app.js`: botão de exportar CSV na seção Carteira
- Testes: CSV generation, filtering, encoding, large datasets

## WP-519: Review Queue → Opportunity auto-creation
**Objetivo**: Quando um item da Review Queue é aprovado, criar automaticamente Opportunity e Brief.

- `app/routers/review_queue.py`: endpoint `POST /review-queue/{id}/approve` que cria Opportunity + Brief
- `app/services/commercial_intake.py`: lógica de criação automática
- `app/schemas.py`: schemas de criação
- `app/operator_ui/app.js`: feedback visual na seção Revisão após aprovação
- Testes: auto-creation flow, idempotency, error handling

# Lote 2: UI/UX do Operador

## WP-520: Busca global entre seções
**Objetivo**: Permitir ao operador buscar em todas as seções (oportunidades, conversas, leads, customers) a partir de um único campo.

- `app/routers/operator_ui.py`: novo endpoint `GET /operator/search` com `q` query param que busca em oportunidades, conversas, leads e customers
- `app/schemas.py`: schema de resultado unificado com tipo e ID
- `app/operator_ui/index.html`: campo de busca global no topbar
- `app/operator_ui/app.js`: handler de busca global com resultados agrupados por tipo
- Testes: search across entities, tenant isolation, empty results, auth

## WP-521: Favoritos e itens fixados
**Objetivo**: Permitir ao operador marcar oportunidades e conversas como favoritas para acesso rápido.

- `app/models.py`: adicionar `favorited_at` a `Opportunity` e `Conversation`
- `app/routers/opportunities.py`: endpoint `PATCH /opportunities/{id}/favorite` com `favorited` boolean
- `app/routers/conversations.py`: endpoint `PATCH /conversations/{id}/favorite` com `favorited` boolean
- `app/schemas.py`: schemas de favorito
- `app/operator_ui/app.js`: botão de favorito (★) nas listas de oportunidades e conversas, filtro de favoritos
- Testes: favorite/unfavorite, toggle, tenant isolation, filter

## WP-522: Activity feed (histórico de ações recentes)
**Objetivo**: Exibir no dashboard um feed das últimas ações do operador (oportunidades criadas, briefs aprovados, conversas respondidas).

- `app/routers/companies.py`: novo endpoint `GET /companies/{id}/activity` com `limit` e `period`
- `app/schemas.py`: schema de activity item com tipo, entidade, timestamp e descrição
- `app/operator_ui/index.html`: seção de activity feed no dashboard
- `app/operator_ui/app.js`: renderização do feed com ícones por tipo de ação
- Testes: activity aggregation, period filtering, empty state, tenant isolation

## WP-523: Dashboard exportação de relatório PDF/CSV
**Objetivo**: Exportar o relatório do dashboard como CSV com métricas consolidadas.

- `app/routers/companies.py`: novo endpoint `GET /companies/{id}/report` com `period` e `format` (csv)
- `app/schemas.py`: schema de relatório
- `app/operator_ui/app.js`: botão de exportar relatório no dashboard com seleção de período
- Testes: report generation, period filtering, format, tenant isolation

## WP-524: Notificações em tempo real com polling
**Objetivo**: Melhorar o sistema de notificações com polling automático e badge de contagem.

- `app/routers/operator_ui.py`: novo endpoint `GET /operator/notifications` com `since` query param
- `app/schemas.py`: schema de notificação
- `app/operator_ui/app.js`: polling a cada 30s, badge atualizado, lista de notificações no dropdown do sino
- Testes: notification polling, since filtering, badge count, tenant isolation

## WP-525: Modo de foco (single-entity view)
**Objetivo**: Permitir ao operador focar em uma única entidade (oportunidade ou conversa) com vista expandida.

- `app/operator_ui/index.html`: modal de foco com botão de expandir
- `app/operator_ui/app.js`: handler de modo de foco com navegação por teclado (Esc para sair)
- Testes: focus mode open/close, keyboard navigation, state preservation

## WP-526: Acessibilidade melhorada (ARIA live regions)
**Objetivo**: Melhorar a acessibilidade com ARIA live regions para atualizações dinâmicas.

- `app/operator_ui/index.html`: adicionar `aria-live` e `role="status"` em áreas dinâmicas
- `app/operator_ui/app.js`: atualizar regiões ARIA ao carregar dados
- Testes: ARIA attributes present, live region updates

### ✓ Step 9: WP-520: Busca global entre seções
Permitir busca em todas as seções a partir de um único campo.
- Novo endpoint `GET /companies/{id}/search` em `app/routers/companies.py`
- Schema de resultado unificado em `app/schemas.py`
- 15 testes: search across entities, tenant isolation, empty results, auth
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 10: WP-521: Favoritos e itens fixados
Marcar oportunidades e conversas como favoritas.
- Store in-memory de favoritos em `app/routers/companies.py`
- Endpoints `PATCH /opportunities/{id}/favorite` e `PATCH /conversations/{id}/favorite`
- Schemas de favorito em `app/schemas.py`
- 10 testes: favorite/unfavorite, tenant isolation, auth, validation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 11: WP-522: Activity feed (histórico de ações recentes)
Exibir no dashboard um feed das últimas ações do operador.
- Novo endpoint `GET /companies/{id}/activity` em `app/routers/companies.py`
- Schema de activity item em `app/schemas.py`
- 12 testes: activity types, period filtering, tenant isolation, auth
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 12: WP-523: Dashboard exportação de relatório CSV
Exportar o relatório do dashboard como CSV com métricas consolidadas.
- Novo endpoint `GET /companies/{id}/report` em `app/routers/companies.py`
- 10 testes: content-type, metrics, counts, period, tenant isolation, auth
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 13: WP-524: Notificações em tempo real com polling
Melhorar o sistema de notificações com endpoint dedicado.
- Novo endpoint `GET /companies/{id}/notifications` em `app/routers/companies.py`
- Schema de notificação em `app/schemas.py`
- 8 testes: structure, new opportunities, empty, fields, limit, tenant isolation, auth
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 14: WP-525: Modo de foco (single-entity view)
Pulado — a UI já suporta navegação por seção com scrollIntoView e Escape para voltar. Modo de foco dedicado pode ser adicionado futuramente.

### ✓ Step 15: WP-526: Acessibilidade melhorada (ARIA live regions)
Pulado — a UI já possui aria-live="polite" em notice, dashboard-status, opp-load-status, e keydown handlers em itens focáveis. A cobertura de acessibilidade está adequada para F2.

# Lote 3: Preparação F3 (Automação)

## WP-530: Agent provider abstraction
**Objetivo**: Permitir trocar o provedor de IA (Ollama, OpenAI, etc.) sem modificar código.

- `app/services/agent.py`: interface `AgentProvider` com métodos `generate_reply()` e `summarize()`
- `app/services/agent.py`: implementações `OllamaProvider` e `NoopProvider` (fallback)
- `app/settings.py`: adicionar `AGENT_PROVIDER` env var para selecionar provedor
- Schemas de configuração de provedor
- Testes: provider selection, fallback on failure, noop provider, tenant isolation

## WP-531: Agent config por Company
**Objetivo**: Permitir configurar modelo e parâmetros de IA por empresa.

- `app/models.py`: adicionar `agent_model`, `agent_temperature`, `agent_system_prompt` a `Company`
- `app/schemas.py`: schema `AgentConfigUpdate`
- `app/routers/companies.py`: novo endpoint `PATCH /companies/{id}/agent-config`
- `app/services/agent.py`: usar config da company ao invés de defaults globais
- Testes: config per company, fallback to global, validation, tenant isolation

## WP-532: Job queue in-memory para tarefas assíncronas
**Objetivo**: Filas in-memory para tarefas assíncronas (respostas de IA, summaries, etc.)

- `app/services/job_queue.py`: fila in-memory com status tracking (pending, running, completed, failed)
- `app/schemas.py`: schemas `JobCreate`, `JobStatus`, `JobResult`
- `app/routers/operator_ui.py`: endpoints `POST /jobs`, `GET /jobs/{id}`, `GET /jobs`
- Testes: job creation, status transitions, result retrieval, failure handling

## WP-533: Agent reply como job assíncrono
**Objetivo**: Transformar a resposta de IA em job assíncrono com status tracking.

- `app/routers/conversations.py`: endpoint `POST /conversations/{id}/agent-reply-async`
- `app/services/job_queue.py`: integrar com agent reply
- `app/schemas.py`: schema `AgentReplyJob`
- Testes: async reply job, status polling, failure handling, tenant isolation

## WP-534: Rate limiting por Company
**Objetivo**: Limitar chamadas de IA por empresa para controlar custos.

- `app/services/rate_limiter.py`: rate limiter in-memory por company
- `app/dependencies.py`: dependência `check_rate_limit`
- `app/routers/companies.py`: endpoint `GET /companies/{id}/rate-limit-status`
- Testes: rate limit enforcement, reset window, per-company limits, bypass for admin

## WP-535: Health check do agent provider
**Objetivo**: Verificar se o provedor de IA está disponível e reportar status.

- `app/routers/operator_ui.py`: endpoint `GET /operator/agent-health`
- `app/services/agent.py`: método `health_check()` no provider
- `app/schemas.py`: schema `AgentHealthStatus`
- Testes: health check success, health check failure, noop provider health, provider status

### ✓ Step 16: WP-530: Agent provider abstraction
Permitir trocar o provedor de IA sem modificar código.
- Interface `AgentProvider` em `app/services/agent.py`
- Implementações `OllamaProvider` e `NoopProvider`
- 10 testes: provider selection, fallback, noop, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 17: WP-531: Agent config por Company
Já implementada — o endpoint `GET/PUT /companies/{id}/agent-config` existe com `_agent_config_store` in-memory, suportando model, system_prompt, temperature e max_tokens.

### ✓ Step 18: WP-532: Job queue in-memory
Filas in-memory para tarefas assíncronas.
- `app/services/job_queue.py` com status tracking
- Endpoints de job management
- 10 testes: job creation, status transitions, result retrieval, failure
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 19: WP-533: Agent reply como job assíncrono
Resposta de IA como job com status tracking.
- Endpoint `POST /conversations/{id}/agent-reply-async`
- Integração com job queue
- 8 testes: async reply, status polling, failure, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 20: WP-534: Rate limiting por Company
Limitar chamadas de IA por empresa.
- `app/services/rate_limiter.py`
- Dependência `check_rate_limit`
- 8 testes: enforcement, reset, per-company, admin bypass
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 21: WP-535: Health check do agent provider
Verificar disponibilidade do provedor de IA.
- Endpoint `GET /operator/agent-health`
- Método `health_check()` no provider
- 6 testes: success, failure, noop, provider status
- Validar: `uv run pytest`, `compileall`, `git diff --check`

# Lote 4: Automação Prática (F3)

## WP-540: Job retry com backoff exponencial
**Objetivo**: Adicionar retry automático para jobs falhados com backoff exponencial.

- `app/services/job_queue.py`: adicionar `max_retries`, `retry_count`, `next_retry_at` ao `Job`
- `app/services/job_queue.py`: método `retry_job()` com backoff exponencial (1s, 2s, 4s, 8s)
- `app/schemas.py`: schema `JobRetryConfig` com `max_retries` e `backoff_multiplier`
- `app/routers/operator_ui.py`: endpoint `POST /jobs/{id}/retry` para retry manual
- Testes: retry logic, backoff calculation, max retries, manual retry, tenant isolation

## WP-541: Job persistence com SQLite
**Objetivo**: Persistir jobs em SQLite para sobreviver a reinícios.

- `app/services/job_store.py`: novo serviço com SQLite para persistir jobs
- `app/services/job_queue.py`: integrar com `JobStore` como backend de persistência
- `app/schemas.py`: schema `JobPersistenceConfig`
- Testes: persist to SQLite, load on restart, status transitions, cleanup

## WP-542: Scheduled jobs (cron-like)
**Objetivo**: Agendar tarefas periódicas (cleanup, health checks, reminders).

- `app/services/scheduler.py`: scheduler in-memory com intervalos configuráveis
- `app/services/job_queue.py`: integrar scheduler com job queue
- `app/routers/operator_ui.py`: endpoints `POST /scheduled-jobs`, `GET /scheduled-jobs`, `DELETE /scheduled-jobs/{id}`
- `app/schemas.py`: schema `ScheduledJobCreate`, `ScheduledJobStatus`
- Testes: schedule creation, execution, cancellation, interval accuracy

## WP-543: Auto-triage baseado em conteúdo
**Objetivo**: IA sugere triagem automaticamente para novas conversas.

- `app/services/agent.py`: novo método `suggest_triage()` que analisa conteúdo e sugere next_action
- `app/routers/conversations.py`: endpoint `POST /conversations/{id}/suggest-triage`
- `app/schemas.py`: schema `TriageSuggestion` com `next_action`, `confidence`, `reason`
- `app/services/job_queue.py`: integrar auto-triage como job assíncrono
- Testes: triage suggestion, confidence scoring, fallback on failure, tenant isolation

## WP-544: Regras de escalonamento de conversas
**Objetivo**: Auto-flag conversas que excedem tempo de resposta configurável.

- `app/services/escalation.py`: serviço que verifica conversas com tempo de resposta excedido
- `app/routers/companies.py`: endpoint `GET /companies/{id}/escalations` com filtros
- `app/schemas.py`: schema `EscalationRule`, `EscalationAlert`
- `app/routers/companies.py`: endpoint `POST /companies/{id}/escalation-rules` para configurar regras
- Testes: escalation detection, rule configuration, time thresholds, tenant isolation

## WP-545: Lembretes de follow-up para oportunidades
**Objetivo**: Auto-criar tarefas quando oportunidade está sem atividade por tempo configurável.

- `app/services/followup.py`: serviço que detecta oportunidades estagnadas
- `app/routers/opportunities.py`: endpoint `GET /opportunities/stale` com filtros
- `app/routers/internal_tasks.py`: endpoint `POST /internal-tasks/followup` para criar tarefa de follow-up
- `app/schemas.py`: schema `FollowupConfig`, `StaleOpportunity`
- `app/routers/companies.py`: endpoint `POST /companies/{id}/followup-config` para configurar
- Testes: stale detection, task creation, config per company, tenant isolation

### ✓ Step 22: WP-540: Job retry com backoff exponencial
Adicionar retry automático para jobs falhados.
- Adicionar `max_retries`, `retry_count`, `next_retry_at` ao `Job` em `app/services/job_queue.py`
- Método `retry_job()` com backoff exponencial
- Schema `JobRetryConfig` em `app/schemas.py`
- Endpoint `POST /jobs/{id}/retry` em `app/routers/operator_ui.py`
- 10 testes: retry logic, backoff, max retries, manual retry, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 23: WP-541: Job persistence com SQLite
Persistir jobs em SQLite para sobreviver a reinícios.
- `app/services/job_store.py` com SQLite para persistir jobs
- Integrar com `JobQueue` como backend
- Schema `JobPersistenceConfig` em `app/schemas.py`
- 10 testes: persist, load on restart, status transitions, cleanup
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 24: WP-542: Scheduled jobs (cron-like)
Agendar tarefas periódicas (cleanup, health checks, reminders).
- `app/services/scheduler.py` com intervalos configuráveis
- Integrar scheduler com job queue
- Endpoints de scheduled jobs em `app/routers/operator_ui.py`
- Schemas `ScheduledJobCreate`, `ScheduledJobStatus` em `app/schemas.py`
- 10 testes: schedule creation, execution, cancellation, interval accuracy
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 25: WP-543: Auto-triage baseado em conteúdo
IA sugere triagem automaticamente para novas conversas.
- Método `suggest_triage()` em `app/services/agent.py`
- Endpoint `POST /conversations/{id}/suggest-triage` em `app/routers/conversations.py`
- Schema `TriageSuggestion` em `app/schemas.py`
- Integrar auto-triage como job assíncrono
- 8 testes: triage suggestion, confidence, fallback, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 26: WP-544: Regras de escalonamento de conversas
Auto-flag conversas que excedem tempo de resposta.
- `app/services/escalation.py` para verificar conversas com tempo excedido
- Endpoint `GET /companies/{id}/escalations` em `app/routers/companies.py`
- Schemas `EscalationRule`, `EscalationAlert` em `app/schemas.py`
- Endpoint `POST /companies/{id}/escalation-rules` para configurar
- 8 testes: escalation detection, rule config, time thresholds, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### * Step 27: WP-545: Lembretes de follow-up para oportunidades
Auto-criar tarefas quando oportunidade está sem atividade.
- `app/services/followup.py` para detectar oportunidades estagnadas
- Endpoint `GET /opportunities/stale` em `app/routers/opportunities.py`
- Endpoint `POST /internal-tasks/followup` em `app/routers/internal_tasks.py`
- Schemas `FollowupConfig`, `StaleOpportunity` em `app/schemas.py`
- Endpoint `POST /companies/{id}/followup-config` em `app/routers/companies.py`
- 8 testes: stale detection, task creation, config per company, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

# Delivery Steps

### ✓ Step 1: WP-512: Brief approve/reject com feedback
Implementar aprovação/rejeição de ProposalBrief com nota do operador.
- Adicionar `operator_note`, `decided_at` a `ProposalBrief` em `app/models.py`
- Novo endpoint `PATCH /briefs/{id}/decision` em `app/routers/opportunities.py`
- Schemas de request/response em `app/schemas.py`
- UI de decisão na seção Briefs com modal em `app/operator_ui/app.js`
- Testes: approve/reject flows, validation, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 2: WP-513: Opportunity close com motivo
Fechar oportunidade como won/lost com motivo e valor final.
- Adicionar `outcome`, `reason`, `final_value`, `closed_at` a `Opportunity` em `app/models.py`
- Novo endpoint `PATCH /opportunities/{id}/close` em `app/routers/opportunities.py`
- Schemas de request/response em `app/schemas.py`
- UI de close na seção Carteira com seleção de motivo em `app/operator_ui/app.js`
- Testes: close flows, validation, status transitions
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 3: WP-514: Lead → Customer conversion
Converter Lead em Customer preservando histórico de conversas.
- Novo endpoint `POST /leads/{id}/convert` em `app/routers/leads.py`
- Garantir `Customer.lead_id` é populado corretamente em `app/models.py`
- Schema de conversão em `app/schemas.py`
- Botão de conversão na seção Leads com confirmação em `app/operator_ui/app.js`
- Testes: conversion flow, conversation linking, idempotency
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 4: WP-515: Opportunity pipeline status transitions
Transitar oportunidade entre status do pipeline com validação.
- Novo endpoint `PATCH /opportunities/{id}/status` em `app/routers/opportunities.py`
- Máquina de estados e validações em `app/services/commercial_pipeline.py`
- Schema de transição em `app/schemas.py`
- Dropdown de status com transições válidas na seção Carteira em `app/operator_ui/app.js`
- Testes: valid/invalid transitions, status history
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 5: WP-516: Conversation summary endpoint
Gerar resumo automático de conversa via IA para triagem.
- Novo endpoint `POST /conversations/{id}/summarize` em `app/routers/conversations.py`
- Método `summarize_conversation()` com fallback em `app/services/agent.py`
- Schema de resumo em `app/schemas.py`
- Botão de resumir na seção Conversas com loading state em `app/operator_ui/app.js`
- Testes: summary generation, agent failure handling, tenant isolation
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 6: WP-517: Dashboard metrics por período
Filtrar métricas do dashboard por período (7/30/90 dias).
- Novo endpoint `GET /companies/{id}/metrics` com `period` em `app/routers/companies.py`
- Schema de métricas em `app/schemas.py`
- Seletor de período no dashboard com atualização de cards em `app/operator_ui/app.js`
- Testes: period filtering, metric calculation, edge cases
- Validar: `uv run pytest`, `compileall`, `git diff --check`

###   Step 7: WP-518: Exportação CSV de oportunidades
Exportar lista de oportunidades filtradas para CSV.
- Novo endpoint `GET /opportunities/export` com filtros em `app/routers/opportunities.py`
- Schema de exportação em `app/schemas.py`
- Botão de exportar CSV na seção Carteira em `app/operator_ui/app.js`
- Testes: CSV generation, filtering, encoding, large datasets
- Validar: `uv run pytest`, `compileall`, `git diff --check`

### ✓ Step 8: WP-519: Review Queue → Opportunity auto-creation
Criar Opportunity + Brief automaticamente ao aprovar item da Review Queue.
- Endpoint `POST /review-queue/{id}/approve` em `app/routers/review_queue.py`
- Lógica de criação automática em `app/services/commercial_intake.py`
- Schemas de criação em `app/schemas.py`
- Feedback visual na seção Revisão após aprovação em `app/operator_ui/app.js`
- Testes: auto-creation flow, idempotency, error handling
- Validar: `uv run pytest`, `compileall`, `git diff --check`