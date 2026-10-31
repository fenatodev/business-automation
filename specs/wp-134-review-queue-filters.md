# WP-134 — Filtros e ordenação na review queue UI

**Data:** 31/10/2026
**Status:** Concluída

## Problema

A review queue na UI tinha paginação (Anterior/Próxima) mas não tinha filtros visíveis de status e ordenação, embora o backend já suportasse `status`, `sort`, `limit`, `offset` e `/count`.

## Solução

Adicionado `rq-filters` com dropdown de status (Todos, Pendente, Aprovado, Rejeitado), dropdown de ordenação (Data, ID, Status) e botão "Limpar". `buildReviewUrl()` e `buildReviewCountUrl()` conectam os filtros ao backend.

## Changes

- `app/operator_ui/index.html`: seção `.rq-filters` com status filter, sort dropdown, clear button
- `app/operator_ui/app.js`: `buildReviewUrl()`, `buildReviewCountUrl()`, `reviewTotal`, listeners de filtro
- `app/operator_ui/styles.css`: `.rq-filters`, `.rq-filter-group` styles
- `tests/test_wp134_review_queue_ui.py`: 17 testes de contrato UI

## Verification

- `uv run pytest`: **1891 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
