# WP-084 — Approve e reject do proposal brief

## Problema

O endpoint de aprovação do proposal brief (WP-071) não estava na chain de WPs
(wp/072→wp/083) e não havia forma de rejeitar um brief aprovado, voltando-o
para rascunho. A UI também não tinha botões de approve/reject.

## Solução

Dois endpoints atômicos em opportunities.py:
- `PATCH /opportunities/{id}/proposal-brief/approve`: aprova brief
  (ready_for_review → approved) e avança opportunity (→ in_progress)
- `PATCH /opportunities/{id}/proposal-brief/reject`: rejeita brief
  (approved/ready_for_review → draft) sem alterar opportunity

UI com botões "Aprovar brief" e "Rejeitar brief" visíveis quando o brief
está ready_for_review ou approved.

## Changes

### Backend (app/routers/opportunities.py)
- `approve_proposal_brief`: atômico, brief → approved, opportunity → in_progress
- `reject_proposal_brief`: brief → draft, opportunity inalterada

### HTML (app/operator_ui/index.html)
- `#brief-actions` com botões approve e reject no brief panel

### JavaScript (app/operator_ui/app.js)
- `displayBrief()`: mostra/esconde botões conforme status; labels para "approved"
- Handlers approve/reject com PATCH e refreshList após sucesso

### Testes (tests/test_brief_approve_reject.py)
- 11 testes: approve success, draft reject, double approve, auth,
  reject ready_for_review, reject approved, reject draft, auth,
  opportunity unchanged, tenant isolation (approve + reject)

## Validação

- **1279 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-084 depende de WP-083 (PR #167). Base do PR: `wp/083-lead-management`.
