# WP-143 — Timeline de atividades da oportunidade

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O operador não via o histórico de ações realizadas em uma oportunidade. Sem uma timeline, era difícil entender a evolução do ciclo de vida.

## Solução

Adicionado endpoint `GET /opportunities/{id}/timeline` que deriva eventos dos dados existentes: criação, triagem (com nota) e mudanças de status do brief. Não requer migration — usa apenas Opportunity e ProposalBrief.

A UI exibe uma seção "Atividades" no painel de detalhes com eventos ordenados por data descendente.

## Changes

- `app/routers/opportunities.py`: novo endpoint `/timeline` com eventos derived
- `app/operator_ui/index.html`: `#opp-timeline-section` com `#opp-timeline-list`
- `app/operator_ui/app.js`: `loadOpportunityTimeline()`, allowlist atualizada
- `app/operator_ui/styles.css`: `.opp-timeline-section`, `.opp-timeline-item`
- `tests/test_opportunity_timeline.py`: 9 testes backend
- `specs/wp-143-opportunity-timeline.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2008 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
