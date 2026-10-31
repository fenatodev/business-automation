# WP-135 — Remover ordenação client-side de conversas

**Data:** 31/10/2026
**Status:** Concluída

## Problema

`showConversationList()` ordenava as conversas no navegador com `.sort((a, b) => b.id - a.id)`, ignorando a ordenação retornada pelo backend. O backend já suporta `?sort=` (WP-080) e a UI já tinha o dropdown `conv-filter-sort` conectado a `buildConversationUrl()`, mas a ordenação client-side sobrescrevia a ordem do servidor.

## Solução

Removida a ordenação client-side redundante em `showConversationList()`. A função agora itera diretamente sobre `conversations`, preservando a ordem retornada pelo backend.

## Changes

- `app/operator_ui/app.js`: removido `.sort()` e variável `ordered` em `showConversationList()`
- `tests/test_wp135_conversation_sort_ui.py`: 15 testes de contrato UI

## Verification

- `uv run pytest`: **1906 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
