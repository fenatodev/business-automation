# WP-151 — Filtro de data em conversas

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O módulo de conversas não tinha filtro por data, impedindo o operador de
trabalhar com janelas temporais específicas.

## Solução

Adicionado `from_date` e `to_date` query params em `GET /conversations`,
`GET /conversations/count` e `GET /conversations/export.csv`. Usa comparação
de strings ISO 8601 compatível com SQLite/PostgreSQL. UI com campos de data
na seção de filtros de conversas.

## Changes

- `app/routers/conversations.py`: from_date, to_date em list, count, export
- `app/operator_ui/index.html`: #conv-from-date, #conv-to-date inputs
- `app/operator_ui/app.js`: convFilterFromDate/ToDate state, URL builders, listeners
- `app/operator_ui/styles.css`: .conv-date-filter
- `tests/test_conversation_date_filter.py`: 7 backend tests
- `specs/wp-151-conversation-date-filter.md`: spec
- `docs/operations/development-continuity.md`: updated

## Verification

- `uv run pytest`: **2049 passed** (7 novos), 2 warnings
- `compileall` ✓
- `git diff --check` ✓
