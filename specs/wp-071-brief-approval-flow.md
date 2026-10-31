# WP-071 — Fluxo de aprovação do proposal brief

Base: `origin/main` (após merge WP-065 a WP-070).
Branch: `wp/071-brief-approval-flow`.

## Motivação

ProposalBrief possui status "draft" e "ready_for_review", mas não há como
o operador aprová-lo e avançar a opportunity para o próximo estágio.
O ciclo F2 (intake → triage → brief → aprovação → entrega) fica incompleto.

## Entrega

### Schemas

- `"approved"` adicionado ao `status` Literal de `ProposalBriefUpdate`.
- `"in_progress"` adicionado ao `next_action` Literal de `OpportunityTriageUpdate`.

### Endpoint de aprovação

- `PATCH /opportunities/{id}/proposal-brief/approve` no router `opportunities.py`.
- Autenticado (`require_operator`), tenant-isolado.
- Fluxo:
  1. Verificar brief existe e pertence à company.
  2. Verificar status é "ready_for_review" (400 se não for).
  3. Atualizar brief status para "approved".
  4. Atualizar opportunity next_action para "in_progress".
  5. Retornar brief atualizado.

### UI — Botão de aprovação

- No painel de brief, quando status é "ready_for_review", exibir botão
  "Aprovar brief e iniciar" que chama o endpoint de aprovação.
- Após aprovação, atualizar UI: brief status "Aprovado", opportunity
  selecionada com next_action "in_progress".

## Design

- Aprovação é atômica: brief e opportunity atualizados no mesmo commit.
- Não é possível aprovar brief em "draft" — exige "ready_for_review" primeiro.
- Após aprovação, brief permanece editável mas com status "approved".
- Operator-only, tenant-isolado, sem exposição pública.

## Aceite

- Testes validam:
  - Aprovação de brief ready_for_review.
  - Rejeição de brief em draft (400).
  - Rejeição de brief já aprovado (400).
  - Opportunity avança para in_progress.
  - Tenant isolation.
- `uv run pytest`, compileall, git diff --check: PASS.

## Próximo passo

Após integração, avaliar se é necessário um histórico de aprovações
(quem aprovou, quando) ou se o timestamp updated_at é suficiente.
