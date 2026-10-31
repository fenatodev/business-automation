# WP-153 — Filtro de data em customers

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O módulo de customers não tinha filtro por data. O operador não podia trabalhar com janelas temporais.

## Solução

`from_date` e `to_date` adicionados aos endpoints list, count e export CSV usando comparação ISO 8601. UI com campos de data na seção de filtros.

## Changes

- `app/routers/customers.py`: `from_date`, `to_date` em list, count, export CSV
- `app/operator_ui/index.html`: `#customer-from-date`, `#customer-to-date`
- `app/operator_ui/app.js`: `fromDate`/`toDate` em `buildCustomerUrl()`, `buildCustomerCountUrl()`, listeners, export CSV com filtros
- `app/operator_ui/styles.css`: `.customer-date-filter`
- `tests/test_customer_date_filter.py`: 6 testes backend
- `specs/wp-153-customer-date-filter.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2063 passed** (6 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
