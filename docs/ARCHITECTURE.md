# Architecture and repository reconciliation

## Status

Accepted direction for the current project phase.

## Canonical repository

`fenatodev/business-automation` remains the canonical product repository.

The existing implementation is not being discarded. Its domain model, API structure, tests and product decisions are useful foundations. Components may be refactored or replaced when evidence justifies it, but the repository history remains the product history.

## Separation of responsibilities

### Product core

Owned by this repository.

Responsibilities:

- Company as the logical tenant root;
- leads, customers, conversations and messages;
- reusable business-automation rules;
- AI/agent orchestration interfaces;
- integration contracts and adapters;
- reusable configuration primitives;
- product-facing API;
- tests and deterministic domain validation.

The core must not become tied to a single customer, industry, ERP, channel, LLM or automation engine.

### ERP / back-office

External domain system integrated through adapters.

Initial dogfooding target:

- ERPNext as the primary back-office/ERP candidate.

ERP responsibilities may include accounting, sales documents, inventory, fiscal/business records and other mature ERP functions that should not be rebuilt casually inside the product core.

The product core must not duplicate ERP responsibilities unless there is a demonstrated product requirement.

### Dolibarr

Dolibarr remains useful as a secondary evaluation and compatibility reference. It is not a second production system of record by default.

Running two overlapping ERPs in production without a specific requirement would introduce unnecessary synchronization and ownership ambiguity.

### n8n

n8n may act as an automation/integration engine.

It is not the source of truth for product domain rules. Business invariants belong in the application/domain layer or in explicitly owned systems of record.

### Local business-automation lab

The existing local lab is an experimental environment for:

- ERPNext setup and lifecycle scripts;
- Dolibarr comparison;
- seed/test flows;
- reproducibility experiments;
- integration discovery.

The lab is not automatically part of the product repository.

Promotion rule:

> A lab artifact enters the canonical repository only after its purpose, ownership, security boundary and validation path are clear.

Vendored third-party repositories and generated runtime state should not be copied into the product repository.

## Client 0

The user's own company is the first production-oriented validation environment.

Client 0 exists to validate:

- lead capture;
- qualification;
- CRM flow;
- customer/conversation history;
- AI-assisted service;
- business automations;
- ERP integration;
- operational reporting;
- repeatable onboarding and configuration.

Client-0-specific secrets and real business data must stay outside the public repository.

Reusable behavior should be represented as configuration or generalized product capability rather than hardcoded company logic.

## Productization path

The project should evolve in this order:

1. **Dogfood** — solve the internal operation with explicit boundaries.
2. **Stabilize** — tests, migrations, security model and observability.
3. **Extract reusable capability** — configuration, adapters and workflows.
4. **Validate externally** — deploy the same core for a real external client.
5. **Package** — repeatable templates, installers, managed service or product modules.
6. **SaaS only if justified** — self-service tenancy, billing and broader platform concerns come later.

## Immediate technical priorities

1. Establish a clean local checkout of the canonical repository.
2. Inventory the current local ERP lab without mutating it.
3. Validate the existing API test suite and migration chain.
4. Define the minimum Client-0 business process before adding features.
5. Define ERPNext ownership boundaries and the first adapter contract.
6. Keep authentication/RBAC/tenant isolation ahead of any public multi-tenant deployment.
7. Replace or refactor the old Ollama-specific integration only when the desired runtime interface is explicit.

## Non-goals for this reconciliation

This step does not:

- migrate ERP data;
- delete the old API;
- merge the ERP lab into the product;
- choose billing or pricing;
- expose the API publicly;
- implement multi-tenancy security;
- introduce a second production ERP;
- make n8n part of the application core.

## Decision rule

When deciding whether a capability belongs in the product core, ask:

> Would this still be useful and correctly owned if the next client used a different ERP, channel, LLM and industry?

If not, it probably belongs in configuration, an adapter, deployment-specific infrastructure or the lab rather than the core.
