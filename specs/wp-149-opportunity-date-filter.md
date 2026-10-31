# WP-149 — Filtro de data em oportunidades

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O módulo de oportunidades não tinha filtro por data, impedindo o operador de
trabalhar com janelas temporais específicas (ex: oportunidades do mês).

## Solução

Adicionado `from_date` e `to_date` query params em `GET /opportunities`,
`GET /opportunities/count` e `GET /opportunities/export.csv`. Usa comparação
de strings ISO 8601 (`captured_at >= from_date`) compatível com SQLite e
PostgreSQL, sem depender de `strftime` ou `cast`.

## Changes

- `app/routers/opportunities.py`: `from_date`, `to_date` em list, count, export
- `tests/test_opportunity_date_filter.py`: 8 testes backend
- `specs/wp-149-opportunity-date-filter.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2024 passed** (8 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
