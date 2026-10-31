# WP-136 — Paginação de mensagens em conversas na UI

**Data:** 31/10/2026
**Status:** Concluída

## Problema

`selectConversation()` carregava todas as mensagens de uma conversa de uma vez, sem paginação. O backend já suporta `limit/offset` e `/count` desde WP-132, mas a UI não usava esses parâmetros.

## Solução

`loadMessages()` carrega mensagens com `limit/offset` e `/count` em paralelo. Controles de paginação (Anterior/Próxima) adicionados no detalhe da conversa, entre as mensagens e o formulário de resposta.

## Changes

- `app/operator_ui/app.js`: `msgOffset`, `msgPageSize`, `msgTotal`; `loadMessages()`, `updateMessagePagination()`; `selectConversation()` reseta `msgOffset`; allowlist atualizada para `/messages/count`
- `app/operator_ui/index.html`: `msg-pagination` com botões Anterior/Próxima
- `tests/test_wp136_message_pagination_ui.py`: 19 testes de contrato UI

## Verification

- `uv run pytest`: **1923 passed**, 3 warnings
- `compileall` ✓
- `git diff --check` ✓
