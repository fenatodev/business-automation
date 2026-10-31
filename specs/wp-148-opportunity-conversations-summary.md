# WP-148 — Contagem de mensagens nas conversas da oportunidade

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O painel de detalhes da oportunidade listava conversas relacionadas (WP-142)
mas não indicava quantas mensagens cada uma tinha, impedindo o operador de
priorizar conversas com mais contexto.

## Solução

`loadOpportunityConversations()` agora carrega as contagens de mensagens
em paralelo via `/conversations/{id}/messages/count` e exibe "N msg" ao
lado do status de cada conversa.

## Changes

- `app/operator_ui/app.js`: `loadOpportunityConversations()` com Promise.all
  para contagens, exibição "N msg" no meta
- `specs/wp-148-opportunity-conversations-summary.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2016 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
