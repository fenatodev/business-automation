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
- Conversation management with search, filter, pagination, sorting, close/reopen, notes, bulk operations, date filter, and export CSV;
- Lead management with status, notes, search, source filter, bulk operations, customer conversion, date filter, and export CSV;
- Customer management with search, sort, pagination, edit, detail view, date filter, and export CSV;
- Opportunity management with search, sort, pagination, bulk triage, status transitions, notes, date filter, and export CSV;
- Proposal briefs with consolidated list view, search, sort, pagination, date filter, bulk status, bulk delete, and export CSV;
- Internal task queue with retry, lease, fencing, 24×7 supervisor, filters, bulk retry, and export CSV;
- Review queue with filters, sort, pagination, date filter, bulk decision, and export CSV;
- Operator UI dashboard with metrics, pipeline view, clickable next actions, notifications, theme toggle, and CSV export;
- CSV import for leads, customers, and opportunities;
- Create opportunity from lead or customer detail panels;
- Agent-reply flow with persisted conversation history;
- Failure handling that preserves user messages when the agent service is unavailable (HTTP 503);
- 2412 pytest tests covering happy paths, invalid relationships, agent-service failures, tenant isolation, and UI contracts.

## Engineering case study

The useful part of this project is not the idea of "AI for business". It is the boundary work required to make automation reliable.

| Engineering concern | Current approach |
| --- | --- |
| Domain modeling | Explicit Company, Opportunity, Lead, Customer, Conversation, Message, InternalTask entities. |
| Tenant-aware data relationships | Company ownership enforced at API level; cross-company misuse returns 403. |
| Authentication | Bearer API keys with role-based access (admin, operator). |
| API failure behavior | Missing resources and invalid ownership return explicit client errors. |
| AI integration failure | Customer input preserved, failed agent output not fabricated, internal details not leaked. |
| Regression protection | 2412 tests cover happy paths, failures, tenant isolation, and UI contracts. |
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
