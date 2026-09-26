# Client 0 flow and ERPNext adapter boundary

## Status

Draft for review.

This document defines the first narrow Client-0 flow for dogfooding the product without copying local ERP lab artifacts into the public repository.

## Goal

Validate a real internal business workflow while preserving the separation between:

- product core;
- ERPNext / back-office;
- n8n / automation infrastructure;
- local ERP lab experiments;
- private operational configuration and data.

The immediate goal is not to build a full ERP or SaaS platform. The immediate goal is to prove the first reusable business-automation loop with clear ownership and testable boundaries.

## First candidate flow

The first Client-0 flow is:

1. capture a lead;
2. qualify the lead;
3. create or update a customer record;
4. preserve conversation/message history;
5. suggest or draft the next follow-up action;
6. hand off only the appropriate back-office event or entity to ERPNext;
7. expose operational status/reporting for the internal operator.

This flow is intentionally small. It should be expanded only after the first version is observable and testable.

## Ownership boundary

### Product core

Owned by this repository.

Responsibilities:

- Company as the tenant/logical owner root;
- Lead lifecycle;
- Customer profile used by the CRM/AI layer;
- Conversation and Message history;
- AI/agent orchestration contracts;
- business-event abstractions;
- adapter interfaces;
- deterministic tests for domain behavior;
- public/product-facing API.

The product core should store product-level CRM state and automation state. It should not silently become the accounting, inventory, fiscal or ERP source of truth.

### ERPNext

External back-office system integrated through an adapter.

Initial responsibilities:

- accepted customer or business party records when they become back-office relevant;
- sales/back-office documents when the workflow reaches that stage;
- mature ERP records that should not be recreated inside the product core.

ERPNext should not own raw lead qualification or AI conversation history by default. It receives structured handoff data from the product core when a business event crosses the ERP boundary.

### n8n

Auxiliary automation engine.

Initial role:

- glue jobs;
- notifications;
- low-risk integrations;
- operator-triggered workflows.

n8n is not the source of truth for product domain rules. Durable business invariants must be represented in the product core or in the external system that explicitly owns them.

### Local ERP lab

The local `business-automation-lab` remains experimental.

Allowed use:

- read-only discovery;
- reproducing ERPNext/Dolibarr setup knowledge;
- identifying adapter candidates;
- testing throwaway seed flows.

Not allowed in this repository without a separate review:

- vendoring third-party ERP repositories;
- committing generated ERP runtime state;
- committing real business data;
- copying lab scripts without defining ownership, security boundary and validation path.

## Initial adapter contract

The first ERPNext adapter should be modeled as an explicit boundary, not direct scattered calls from domain code.

Candidate interface shape:

```text
Product core event -> ERPNext adapter command -> ERPNext API/client -> adapter result
```

Candidate commands:

- `upsert_business_party`
- `create_sales_opportunity` or equivalent, only after the CRM stage justifies it;
- `record_backoffice_handoff_status`

Candidate event inputs:

- company id / tenant id;
- customer id;
- lead id when applicable;
- normalized contact fields;
- business status;
- source channel metadata;
- idempotency key;
- correlation id.

Candidate adapter result:

- success/failure;
- external ERPNext doctype/name/id;
- idempotency/correlation key;
- normalized error category;
- retryability flag;
- timestamp.

## Idempotency and ownership

Every ERP handoff must have an idempotency key. Retrying the same business event must not create duplicate ERP records.

The product core owns:

- internal ids;
- CRM lifecycle;
- conversation history;
- adapter request status;
- correlation to ERPNext external ids.

ERPNext owns:

- ERP document lifecycle after handoff;
- accounting/inventory/fiscal semantics;
- ERP-native validation failures.

## Data policy

Do not commit real Client-0 data.

Examples and tests should use synthetic companies, leads, customers and conversations. Credentials and deployment configuration stay outside the public repository.

## Acceptance criteria for the first implementation PR

Before implementation begins, the repository should have:

- one testable use case for lead-to-customer flow;
- one explicit adapter interface or port;
- one fake/in-memory ERPNext adapter for tests;
- no dependency on a live ERPNext instance in unit tests;
- no hardcoded Client-0 private data;
- no n8n workflow treated as product-domain source of truth.

## Open questions

- Which exact Client-0 lead source should be implemented first?
- What is the first ERPNext record that should be created or updated?
- What minimum operator UI or API response is needed to make the flow useful?
- Which fields are mandatory for the first handoff?
- Which failures should be retried automatically, and which require operator review?
