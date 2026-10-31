# WP-150 — Filtro de data em oportunidades na UI

**Data:** 31/10/2026
**Status:** Concluída

## Problema

A WP-149 adicionou `from_date` e `to_date` ao backend de oportunidades, mas a UI do operador não tinha campos para usar esses filtros. O operador não podia filtrar oportunidades por janela temporal.

## Solução

Dois campos de data (de/até) na toolbar de oportunidades, conectados a `refreshList()` e `buildOppCountUrl()`. Botão "Limpar filtros" reseta todos os filtros (busca, data, ordenação, arquivadas, pipeline). Exportação CSV respeita os filtros de data.

## Changes

- `app/operator_ui/index.html`: `#opp-from-date`, `#opp-to-date` inputs, `#opp-clear-filters` button
- `app/operator_ui/app.js`: `fromDate`/`toDate` em `refreshList()` params e countParams; event listeners; clear filters handler; export CSV com filtros
- `app/operator_ui/styles.css`: `.opp-date-filter`, `.opp-clear-filters-btn`
- `tests/test_wp150_opportunity_date_filter_ui.py`: 18 testes de contrato UI
- `specs/wp-150-opportunity-date-filter-ui.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2042 passed** (18 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
