# business-automation

**Reusable backend foundation for CRM, business automation, and AI-assisted operational workflows.**

This repository is a practical backend engineering project built around real business-automation use cases. The current implementation focuses on a FastAPI API, relational domain modeling, tested business rules, and a bounded integration point for a local AI agent.

## What is implemented

- FastAPI application with company, lead, customer, conversation, and message flows;
- SQLAlchemy models and PostgreSQL-oriented persistence;
- Alembic migrations;
- API-level business rules for ownership and cross-company consistency;
- agent-reply flow with persisted conversation history;
- failure handling that preserves user messages when the agent service is unavailable;
- tests that verify expected behavior and prevent internal agent-service details from leaking through the API.

## Engineering case study

The useful part of this project is not the idea of "AI for business". It is the boundary work required to make automation reliable.

| Engineering concern | Current approach |
| --- | --- |
| Domain modeling | Explicit Company, Lead, Customer, Conversation and Message entities. |
| Tenant-aware data relationships | Company ownership is represented explicitly and cross-company misuse is rejected by API rules. |
| API failure behavior | Missing resources and invalid ownership relationships return explicit client errors. |
| AI integration failure | Customer input is preserved, failed agent output is not fabricated, and internal service details are not returned to clients. |
| Regression protection | Pytest API tests cover happy paths, invalid relationships and agent-service failures. |
| Product boundaries | ERP and automation engines remain external integrations instead of being reimplemented in the core. |

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

That pattern reflects the broader engineering approach used across my projects: **reproduce the failure, define the boundary, test the behavior, and avoid claiming guarantees that are not implemented.**

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

## Architecture direction

The repository is intended to remain a reusable core rather than a monolithic ERP.

- **Core:** CRM entities, conversations, AI-assisted workflows, reusable business rules.
- **ERP:** ERPNext is the primary back-office integration target; Dolibarr remains an alternative for evaluation.
- **Automation:** n8n may coordinate integrations and workflows without becoming the domain authority.
- **AI runtime:** local/replaceable agent integration behind an explicit service boundary.

## Current limitations

This is an active engineering project, not a production-ready SaaS.

Known gaps include:

- authentication and RBAC are not complete;
- multi-tenant isolation is not yet a security boundary;
- migration history still needs clean-database validation;
- the current local-agent integration should not be treated as the final runtime contract.

These limitations are kept explicit because roadmap intent is not implementation evidence.

## Repository map

```text
app/            FastAPI application, models, routers and services
migrations/     Alembic migration history
tests/          API and failure-path regression tests
docs/           product, roadmap, architecture and decision records
src/            package entry point
```

## Development

Install the project with your preferred `uv` workflow and run the test suite:

```bash
pytest
```

Review the supporting documents for current direction:

- [Product](docs/PRODUCT.md)
- [Roadmap](docs/ROADMAP.md)
- [Decisions](docs/DECISIONS.md)
- [Architecture](docs/ARCHITECTURE.md)

## Security and data

This repository is public.

- do not commit customer data, credentials, tokens or private operational configuration;
- do not treat a client-supplied `company_id` as authorization;
- authenticated access, RBAC and real tenant isolation are required before public deployment.
