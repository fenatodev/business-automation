# WP-144 — Leads relacionados à oportunidade

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O painel de detalhes da oportunidade não mostrava os leads da mesma company, impedindo o operador de ver o contexto de prospectos antes de tomar decisões de triagem.

## Solução

Adicionado endpoint `GET /opportunities/{id}/leads` que retorna até 50 leads da mesma company que a oportunidade, ordenados por ID descendente. A UI exibe uma seção "Leads relacionados" no painel de detalhes, com itens clicáveis que navegam para a seção de leads.

## Changes

- `app/routers/opportunities.py`: novo endpoint `/leads` tenant-isolado
- `app/operator_ui/index.html`: `#opp-leads-section` com `#opp-leads-list`
- `app/operator_ui/app.js`: `loadOpportunityLeads()`, allowlist atualizada
- `app/operator_ui/styles.css`: `.opp-leads-section`, `.opp-lead-item`
- `tests/test_opportunity_leads.py`: 8 testes backend
- `specs/wp-144-opportunity-related-leads.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2016 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
