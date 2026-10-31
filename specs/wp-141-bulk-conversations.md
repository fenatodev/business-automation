# WP-141 — Operações em massa em conversas

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O operador só podia fechar/reabrir uma conversa de cada vez. Com muitas conversas, isso era trabalhoso.

## Solução

Novo endpoint `POST /conversations/bulk-status` aceita 1-100 IDs e atualiza o status (open/closed) de forma tenant-isolada. UI com checkboxes na lista de conversas e barra de ação em massa com seletor de status.

## Changes

- `app/schemas.py`: `ConversationBulkStatus` schema
- `app/routers/conversations.py`: `POST /conversations/bulk-status`
- `app/operator_ui/index.html`: checkboxes na lista, `#conv-bulk-bar`
- `app/operator_ui/app.js`: `selectedConvIds`, `updateConvBulkBar()`, apply/clear handlers
- `app/operator_ui/styles.css`: `.conv-item-row`, `.conv-checkbox`, `.conv-bulk-bar`
- `tests/test_bulk_conversation_status.py`: 8 testes backend
- `specs/wp-141-bulk-conversations.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **1991 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
