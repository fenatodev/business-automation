# WP-140 — Notas internas em conversas

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O operador não podia registrar notas internas em conversas. Para anotar contexto sobre uma conversa, era necessário usar ferramentas externas, perdendo o rastreabilidade dentro do sistema.

## Solução

Adicionado campo `note` opcional ao schema `ConversationUpdate`. Ao salvar uma nota, ela é armazenada como uma mensagem com `sender_type="system"` e prefixo "📝 Nota interna: ", evitando a necessidade de migration. Endpoint `GET /conversations/{id}/note` retorna a nota mais recente.

A UI exibe um campo de nota interna no painel de detalhes da conversa, com botão "Salvar nota" e feedback visual.

## Changes

- `app/schemas.py`: `ConversationUpdate` com `note` opcional (max 2000 chars); `status` tornado opcional
- `app/routers/conversations.py`: `PATCH /conversations/{id}` salva nota como Message system; novo `GET /conversations/{id}/note`
- `app/operator_ui/index.html`: `#conv-note-section` com textarea e botão salvar
- `app/operator_ui/app.js`: `loadConversationNote()`, save note listener, allowlist atualizada, disconnect cleanup
- `app/operator_ui/styles.css`: `.conv-note-section` styles
- `tests/test_conversation_notes.py`: 11 testes backend
- `specs/wp-140-conversation-notes.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **1983 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
