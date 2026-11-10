# business-automation

**FastAPI backend for reusable CRM, business automation, and AI-assisted workflows.**

Plataforma reutilizável de automação de negócios, CRM e IA.

O projeto tem dois objetivos complementares:

1. estruturar e automatizar a operação da própria empresa como **Client 0**;
2. transformar as capacidades validadas em serviços, integrações e produtos de automação reutilizáveis para outros clientes.

## What is implemented

- FastAPI application with multi-tenant CRM domain modeling;
- SQLAlchemy models and PostgreSQL-oriented persistence with Alembic migrations;
- Bearer token authentication with API keys (SHA-256) and tenant isolation by Company;
- Complete commercial cycle F2: intake → opportunity → triage → proposal brief → approval → in progress → done/lost;
- Conversation management with search, filter (including by customer), pagination, sorting, close/reopen, notes, bulk operations, date filter, and export CSV;
- Lead management with status, notes, search, source filter, bulk operations, customer conversion, date filter, and export CSV;
- Customer management with search, sort, pagination, edit, detail view, date filter, and export CSV;
- Opportunity management with search, sort, pagination, bulk triage, status transitions, notes, date filter, and export CSV;
- Proposal briefs with consolidated list view, search, sort, pagination, date filter, bulk status, bulk delete, and export CSV;
- Internal task queue with retry, lease, fencing, 24×7 supervisor, filters, bulk retry, and export CSV;
- Review queue with filters, sort, pagination, date filter, bulk decision, and export CSV;
- Operator UI dashboard with metrics, pipeline view, source breakdowns, clickable next actions, notifications, theme toggle, and CSV export;
- CSV import for leads, customers, and opportunities;
- Create opportunity from lead or customer detail panels;
- Agent-reply flow with persisted conversation history;
- Configurable agent: system prompt, temperature (0.0-2.0), max tokens, model selection with validation, fallback on missing model, available models endpoint, and per-company configuration (F3 preparation);
- Agent configuration UI in operator panel with system prompt, temperature, max tokens, and model selector dropdown;
- Agent usage tracking with per-company success/failure stats visible in the dashboard;
- Brief detail panel with back button, title, and related conversations;
- Suggest agent reply button in conversation UI (WP-227) — triggers AI suggestion without persisting;
- Recent activities feed in dashboard (WP-228) — shows last 20 activities across opportunities, conversations, and leads;
- Failure handling that preserves user messages when the agent service is unavailable (HTTP 503);
- Bulk delete for review queue items (WP-230) — clean up decided items in bulk;
- Filter conversations by lead (WP-232) — dropdown and backend `?lead_id=` in list, count, export CSV;
- Filter proposal briefs by opportunity (WP-233) — backend `?opportunity_id=` in list, count, export CSV;
- Filter briefs by opportunity in UI (WP-234) — dropdown populated from opportunities;
- Create customer from conversation (WP-235) — button and form in conversation detail panel;
- Create opportunity from conversation (WP-236) — button and form in conversation detail panel;
- AI-assisted triage suggestion (WP-237) — `POST /opportunities/{id}/suggest-triage` uses agent to suggest next action;
- AI-assisted intake suggestion (WP-258/259) — `POST /internal/commercial-intake/suggest` predicts intent and category before creating the opportunity;
- Business performance metrics in dashboard (WP-256/257) — lead conversion rate, opportunity closure rate, brief approval rate;
- Extended keyboard shortcuts (WP-260) — Ctrl+1-0 navigates all 10 operator sections (Dashboard to Agent config);
- Reply templates (WP-264) — reusable response templates with UI selector in conversation replies;
- Reply templates management (WP-265) — create, list, and delete reusable response templates in the agent config UI;
- Opportunity lead/customer filtering (WP-263) — `?lead_id=` and `?customer_id=` in GET /opportunities with UI dropdowns;
- Lead name sorting (WP-261) — `?sort=name` in GET /leads with UI dropdown option;
- Brief title sorting (WP-262) — `?sort=title` in GET /proposal-briefs with UI dropdown option;
- Consolidated dashboard CSV export (WP-275) — single CSV with all dashboard metrics;
- Opportunity progress bar (WP-276) — visual cycle progress indicator in opportunity detail panel;
- Failed tasks badge in notifications (WP-277) — failed internal tasks appear in notification polling and task section badge;
- Create conversation from opportunity (WP-278) — form with AI-assisted message suggestion in opportunity detail panel;
- AI-assisted lead suggestion from conversation (WP-267) — `POST /conversations/{id}/suggest-lead` extracts lead info from messages;
- AI-assisted customer suggestion from conversation (WP-268) — `POST /conversations/{id}/suggest-customer` extracts customer info from messages;
- AI-assisted opportunity suggestion from conversation (WP-269) — `POST /conversations/{id}/suggest-opportunity` extracts opportunity info from messages;
- AI-assisted opportunity suggestion from lead (WP-271) — `POST /leads/{id}/suggest-opportunity` generates opportunity fields from lead data;
- AI-assisted opportunity suggestion from customer (WP-272) — `POST /customers/{id}/suggest-opportunity` generates opportunity fields from customer data;
- AI-assisted lead suggestion from customer (WP-273) — `POST /customers/{id}/suggest-lead` generates lead fields from customer data;
- AI-assisted conversation message suggestion (WP-274) — `POST /conversations/suggest-message` suggests opening message for new conversations;
- Conversation summary by AI — `POST /conversations/{id}/summarize` generates summary, key points, and action items;
- Opportunity priority score (WP-238) — auto-calculated 0-100 score based on deadline, budget, status, source;
- Opportunity priority filter (WP-266) — `?priority_level=` (high/medium/low) in list, count, export CSV;
- Opportunity priority in export CSV (WP-246) — includes score and level columns;
- High priority opportunities in dashboard (WP-239) — shows urgent opportunities on dashboard;
- Bulk AI triage suggestion (WP-247/249) — `POST /opportunities/bulk-suggest-triage` for 1-100 opportunities;
- AI brief suggestion (WP-240/241) — `POST /opportunities/{id}/suggest-brief` with UI button and auto-fill;
- Briefs metrics in dashboard (WP-244) — brief count by status on dashboard;
- Briefs ready for review in next actions (WP-245) — alerts operator to briefs needing review;
- Detailed brief export CSV (WP-250) — 12 columns including diagnosis, scope, deliverables, criteria;
- Browser title notification badge — shows pending count in browser tab title;
- Auto AI suggestion on reply form (WP-252) — loads AI suggestion when opening reply form;
- Section keyboard shortcuts (WP-253) — Ctrl+1-7 navigates between operator sections;
- Lead source filter (WP-277) — `?source=` in GET /leads with UI dropdown;
- Opportunity priority filter in UI (WP-266) — dropdown for filtering by high/medium/low priority;
- Conversation triage suggestion — `POST /conversations/{id}/suggest-triage` suggests next action for conversations;
- Follow-up tasks — automatic follow-up task creation based on conversation context;
- Scheduled jobs — cron-like periodic tasks for recurring operations;
- SQLite job persistence — durable storage for scheduled jobs;
- Conversation escalation rules — automatic escalation based on response time and priority;
- Auto-triage for conversations — AI suggests triage action when conversation is created;
- Conversation favorites (WP-279) — toggle favorite (★/☆) on conversations with visual star button;
- 3657 pytest tests covering happy paths, invalid relationships, agent-service failures, tenant isolation, and UI contracts.

## Engineering case study

The useful part of this project is not the idea of "AI for business". It is the boundary work required to make automation reliable.

| Engineering concern | Current approach |
| --- | --- |
| Domain modeling | Explicit Company, Opportunity, Lead, Customer, Conversation, Message, InternalTask entities. |
| Tenant-aware data relationships | Company ownership enforced at API level; cross-company misuse returns 403. |
| Authentication | Bearer API keys with role-based access (admin, operator). |
| API failure behavior | Missing resources and invalid ownership return explicit client errors. |
| AI integration failure | Customer input preserved, failed agent output not fabricated, internal details not leaked. |
| Regression protection | 3657 tests cover happy paths, failures, tenant isolation, UI contracts, cross-module creation, AI-assisted triage and intake suggestion. |
| Product boundaries | ERP and automation engines remain external integrations. |

### Example evaluation mindset

One tested failure path is deliberately more important than a demo-only happy path:

```text
customer message
→ persist input
→ call agent service
→ agent service fails
→ return bounded 503
→ preserve customer message
→ do not persist fake agent output
→ do not leak internal endpoint/model details
```

That pattern reflects the broader engineering approach: **reproduce the failure, define the boundary, test the behavior.**

## Relação com ERP e automação

O produto não pretende reimplementar um ERP completo.

- **ERPNext** é o back-office padrão inicial, com implantação e integração a validar;
- **n8n** pode ser usado como motor auxiliar de integração e automação, sem virar o domínio central;
- este repositório concentra o core reutilizável de CRM, IA, automações e adapters.

**Cobrança de serviços faz parte da operação atual do Client 0**, inicialmente por processo humano e back-office.

## Segurança e dados

Este repositório é público. Portanto:

- não armazenar dados reais de clientes;
- não versionar `.env`, credenciais, tokens ou chaves;
- não tratar `company_id` enviado pelo cliente como autorização;
- autenticação Bearer e isolamento tenant por Company estão implementados para o piloto privado;
- a API continua **não autorizada para exposição pública**.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL / psycopg
- Alembic
- Pydantic Settings
- HTTPX
- Pytest
- uv
- Ollama (local AI agent, optional)

## Architecture direction

The repository is intended to remain a reusable core rather than a monolithic ERP.

- **Core:** CRM entities, conversations, AI-assisted workflows, reusable business rules.
- **ERP:** ERPNext is the primary back-office integration target.
- **Automation:** n8n may coordinate integrations without becoming the domain authority.
- **AI runtime:** local/replaceable agent integration behind an explicit service boundary.

## Current limitations

This is an active engineering project, not a production-ready SaaS.

Known gaps include:

- multi-tenant isolation needs production validation;
- ERPNext integration is not yet implemented;
- n8n workflow remains inactive pending authorization;
- real backup with Restic is gated but not yet executed;
- CI with disposable PostgreSQL is blocked by GitHub scope.

## Repository map

```text
app/            FastAPI application, models, routers, services, operator UI
migrations/     Alembic migration history
tests/          API, integration, and UI contract regression tests
docs/           product, roadmap, architecture and decision records
scripts/        Demo scripts, supervisor runner, utilities
specs/          Work package specifications
ops/            Infrastructure templates (VPS, Docker Compose)
```

## Development

Install the project with `uv` and run the test suite:

```bash
uv run pytest
```

Regras operacionais e validações do repositório estão em [AGENTS.md](AGENTS.md).

Consulte também:

- [Produto](docs/PRODUCT.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisões](docs/DECISIONS.md)
- [Arquitetura vigente](docs/ARCHITECTURE.md)
- [Architecture Baseline v1](docs/architecture/baseline-v1.md)
