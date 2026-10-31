# WP-152 — Filtro de data em leads

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O módulo de leads não tinha filtro por data. O operador não podia trabalhar com janelas temporais.

## Solução

`from_date` e `to_date` adicionados aos endpoints list, count e export CSV usando comparação ISO 8601. UI com campos de data na seção de filtros.

## Changes

- `app/routers/leads.py`: `from_date`, `to_date` em list, count, export CSV
- `app/operator_ui/index.html`: `#lead-from-date`, `#lead-to-date`
- `app/operator_ui/app.js`: `fromDate`/`toDate` em `refreshLeads()`, listeners, export CSV com filtros
- `app/operator_ui/styles.css`: `.lead-date-filter`
- `tests/test_lead_date_filter.py`: 8 testes backend
- `specs/wp-152-lead-date-filter.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2057 passed** (8 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
