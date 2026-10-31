# WP-155 — Filtro de data em internal tasks

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O módulo de internal tasks não tinha filtro por data. O operador não podia trabalhar com janelas temporais.

## Solução

`from_date` e `to_date` adicionados aos endpoints list, count e export CSV usando comparação ISO 8601. Service layer atualizado para suportar os parâmetros. UI com campos de data na seção de filtros.

## Changes

- `app/services/internal_tasks.py`: `from_date`, `to_date` em `list_tasks()`, `task_count()`
- `app/routers/internal_tasks.py`: `from_date`, `to_date` em list, count, export CSV
- `app/operator_ui/index.html`: `#task-from-date`, `#task-to-date`
- `app/operator_ui/app.js`: `fromDate`/`toDate` em `buildTaskUrl()`, `buildTaskCountUrl()`, listeners, export CSV
- `app/operator_ui/styles.css`: `.task-date-filter`
- `tests/test_internal_task_date_filter.py`: 6 testes backend
- `specs/wp-155-task-date-filter.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2075 passed** (12 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
