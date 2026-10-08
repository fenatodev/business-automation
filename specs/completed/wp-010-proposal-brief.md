# WP-010 — Proposal Brief interno para revisão humana

Status: concluído  
Fase: F2 — primeiro ciclo Client 0 assistido  
Base: `origin/main` atual no início da execução

## Problema

WP-009 permite capturar e triar uma Opportunity até `prepare_proposal`, mas ainda não existe um artefato interno que concentre diagnóstico técnico, escopo e evidência para preparar a proposta formal.

A proposta formal, preço, impostos, condições e envio não pertencem ao core neste momento: continuam sob autoridade do ERPNext/back-office e decisão humana, conforme ADR 0001.

## Decisão

Adicionar um `ProposalBrief` interno e tenant-safe, vinculado 1:1 a uma `Opportunity`.

O brief:

- é material interno de preparação;
- não é quotation/proposta formal;
- não contém preço, moeda, imposto ou condição de pagamento;
- não representa aprovação humana;
- não representa envio;
- não cria Lead/Customer;
- não chama ERP;
- não chama IA.

## Pré-condição

Só é permitido criar brief quando:

```text
Opportunity.next_action == "prepare_proposal"
```

Caso contrário:

- responder 409;
- detail: `Opportunity is not ready for proposal preparation`.

## Schema

Nova tabela `proposal_briefs`:

- `id INTEGER PK`;
- `opportunity_id INTEGER NOT NULL FK opportunities.id`;
- `offer_reference VARCHAR(120) NOT NULL`;
- `diagnosis TEXT NOT NULL`;
- `scope TEXT NOT NULL`;
- `deliverables TEXT NOT NULL`;
- `acceptance_criteria TEXT NOT NULL`;
- `assumptions TEXT NULL`;
- `risks TEXT NULL`;
- `status VARCHAR(30) NOT NULL DEFAULT 'draft'`;
- `created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`;
- `updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`.

Constraint:

```text
UNIQUE(opportunity_id)
```

nome explícito:

`uq_proposal_briefs_opportunity_id`

Não duplicar `company_id` no brief. O tenant é herdado da Opportunity, assim como Message herda Company de Conversation.

Toda consulta de brief deve provar tenant via Opportunity.

## Status permitido

Somente:

- `draft`;
- `ready_for_review`.

Não adicionar:

- approved;
- rejected;
- sent;
- accepted;
- won;
- paid.

Esses estados pertencem a etapas posteriores e/ou sistemas autoritativos diferentes.

## Contrato API

### POST /opportunities/{opportunity_id}/proposal-brief

Operator only.

Payload:

```json
{
  "offer_reference": "client0-automation-integration-v1",
  "diagnosis": "O processo atual exige trabalho manual repetitivo.",
  "scope": "Automatizar entrada, validação e handoff.",
  "deliverables": "Fluxo implementado, testes e runbook.",
  "acceptance_criteria": "Fluxo executa do início ao fim com evidência.",
  "assumptions": "Acesso às APIs necessárias será fornecido.",
  "risks": "Provider externo pode impor rate limit."
}
```

Regras:

- Opportunity deve existir no tenant do operator;
- Opportunity deve estar em `prepare_proposal`;
- só um brief por Opportunity;
- duplicate => 409 `Proposal brief already exists`;
- status inicial = `draft`;
- payload não aceita `company_id`;
- payload não aceita preço, moeda, imposto, condição de pagamento, status de envio ou ID ERP.

Usar schema Pydantic com `extra="forbid"`.

### GET /opportunities/{opportunity_id}/proposal-brief

Operator only.

- Opportunity de outro tenant => 404 `Opportunity not found`;
- Opportunity própria sem brief => 404 `Proposal brief not found`;
- retorna o brief interno.

### PATCH /opportunities/{opportunity_id}/proposal-brief

Operator only.

Payload completo do conteúdo editável:

```json
{
  "offer_reference": "client0-automation-integration-v1",
  "diagnosis": "Diagnóstico revisado.",
  "scope": "Escopo revisado.",
  "deliverables": "Entregáveis revisados.",
  "acceptance_criteria": "Critérios revisados.",
  "assumptions": null,
  "risks": "Risco revisado.",
  "status": "ready_for_review"
}
```

Regras:

- Opportunity de outro tenant => 404;
- brief inexistente => 404;
- status apenas `draft|ready_for_review`;
- marcar `ready_for_review` não significa aprovação;
- nenhum efeito externo ocorre.

## Tenant boundary

Não armazenar `company_id` no brief.

Para POST/GET/PATCH:

1. localizar Opportunity por:
   - `Opportunity.id == opportunity_id`;
   - `Opportunity.company_id == identity.company_id`;
2. se não existir, 404;
3. só depois consultar/criar/alterar o brief.

Admin:

- não tem acesso implícito;
- POST/GET/PATCH => 403.

Sem credencial:

- 401.

## Migration

Criar migration linear após `c1f8b4d2a7e9`.

Ela deve:

- criar somente `proposal_briefs`;
- FK para `opportunities.id`;
- unique explícito em `opportunity_id`;
- não alterar Opportunity nem outras tabelas;
- downgrade remover somente `proposal_briefs`;
- manter exatamente um Alembic head.

Não editar migration histórica.

## Arquivos autorizados

Somente:

- `app/models.py`;
- `app/schemas.py`;
- `app/routers/opportunities.py`;
- nova migration em `migrations/versions/`;
- `tests/test_api.py`.

Não precisa novo router.

## Testes obrigatórios

Adicionar testes para:

1. operator cria brief em Opportunity `prepare_proposal`;
2. status inicial é `draft`;
3. Opportunity em `pending|ignore|follow` não permite criação => 409;
4. duplicate brief => 409;
5. operator lê próprio brief;
6. operator atualiza conteúdo e muda para `ready_for_review`;
7. cross-tenant POST via opportunity_id => 404;
8. cross-tenant GET => 404;
9. cross-tenant PATCH => 404;
10. admin POST/GET/PATCH => 403;
11. sem credencial => 401;
12. payload com `company_id` => 422;
13. payload com `price` ou equivalente extra => 422;
14. status fora de `draft|ready_for_review` => 422.

Não reduzir testes existentes.

## Validação obrigatória

```bash
uv run pytest
.venv/bin/python -m compileall app tests migrations
uv run alembic heads
bash scripts/verify-alembic-postgres.sh
git diff --check
```

Acceptance:

- suíte completa verde;
- exatamente um Alembic head;
- harness PostgreSQL passa no novo head;
- nenhum container de validação permanece;
- diff apenas nos cinco grupos autorizados.

## Segunda revisão obrigatória

Como altera schema e superfície tenant-scoped, revisão independente deve verificar:

- migration/downgrade;
- herança de tenant via Opportunity;
- impossibilidade de cross-tenant;
- ausência de `company_id` client-controlled;
- `extra="forbid"`;
- ausência de preço/financeiro;
- status sem semântica de aprovação/envio;
- duplicate 1:1;
- admin sem bypass.

## Não objetivos

Não implementar:

- proposta formal;
- preço;
- imposto;
- moeda;
- termos de pagamento;
- aprovação;
- envio;
- aceite;
- ERPNext;
- Opportunity -> Lead;
- IA geradora de proposta;
- PDF/DOCX;
- frontend;
- automação externa.

## Stop conditions

Parar se:

- precisar alterar auth/dependencies;
- precisar alterar migration histórica;
- for necessário adicionar preço/financeiro ao core;
- for necessário duplicar `company_id` para fazer tenant isolation funcionar;
- harness revelar drift não causado pela migration nova.

## Git

Branch:

`wp/010-proposal-brief`

Commit sugerido:

`feat: add internal proposal brief`

Não mergear localmente.


## Resultado

Concluído em 2026-10-08.

- branch: `wp/010-proposal-brief`;
- PR: #38;
- merge commit: `6a26700f856b60b6c4310684a0af8c2bb8e80b38`;
- `ProposalBrief` interno criado 1:1 com `Opportunity`;
- tenant herdado exclusivamente da Opportunity;
- criação permitida somente em `prepare_proposal`;
- status limitado a `draft|ready_for_review`;
- payload usa `extra="forbid"`;
- nenhum campo de preço, moeda, imposto, pagamento, aprovação, envio ou ERP foi adicionado;
- admin continua sem acesso implícito;
- cross-tenant POST/GET/PATCH retorna 404 pela Opportunity;
- migration linear adicionada após `c1f8b4d2a7e9`;
- `uv run pytest`: 25 passed;
- compileall passou;
- Alembic head único: `d7a4c6e91b20`;
- harness PostgreSQL passou:
  - `FRESH_DATABASE_UPGRADE_OK`;
  - `LEGACY_BASELINE_UPGRADE_OK`;
  - `AMBIGUOUS_COMPANY_MAPPING_REJECTED`;
  - `ALEMBIC_RECOVERY_VERIFIED`;
- cleanup sem containers remanescentes;
- segunda revisão independente: sem blockers e `OK_TO_MERGE: yes`.
