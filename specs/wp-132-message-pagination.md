# WP-132 — Paginação de mensagens em conversas

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O endpoint `GET /conversations/{id}/messages` carregava todas as mensagens de uma conversa de uma vez, sem paginação. Conversas com muitas mensagens consumiam memória excessiva e causavam lentidão.

## Solução

Adicionado `limit` (default 50, max 100) e `offset` (default 0) em `list_messages`.
Novo endpoint `GET /conversations/{id}/messages/count` para controles de paginação.

## Changes

- `app/routers/conversations.py`: `limit`/`offset` em `list_messages`; novo `count_messages`
- `tests/test_message_pagination.py`: 10 testes (paginação, count, tenant isolation, validação)

## Verification

- `uv run pytest`: **1863 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
