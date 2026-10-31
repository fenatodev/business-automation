# WP-154 — Filtro de data em review queue

**Data:** 31/10/2026
**Status:** Concluída

## Problema

A review queue não tinha filtro por data. O operador não podia trabalhar com janelas temporais.

## Solução

`from_date` e `to_date` adicionados aos endpoints list, count e export CSV usando comparação ISO 8601. UI com campos de data na seção de filtros.

## Changes

- `app/routers/review_queue.py`: `from_date`, `to_date` em list, count, export CSV
- `app/operator_ui/index.html`: `#rq-from-date`, `#rq-to-date`
- `app/operator_ui/app.js`: `fromDate`/`toDate` em `buildReviewUrl()`, `buildReviewCountUrl()`, listeners, export CSV
- `app/operator_ui/styles.css`: `.rq-date-filter`
- `tests/test_review_queue_date_filter.py`: 6 testes backend
- `specs/wp-154-review-date-filter.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2075 passed** (12 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
