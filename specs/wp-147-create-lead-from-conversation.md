# WP-147 — Criar lead a partir de conversa

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O operador via conversas mas não podia criar um lead diretamente a partir delas. Tinha que sair da seção de conversas, ir para leads e preencher o formulário manualmente.

## Solução

Botão "+ Criar lead desta conversa" no painel de detalhes da conversa abre formulário inline com nome, telefone, fonte e interesse. A fonte é pré-preenchida com o canal da conversa. Após criar, a lista de leads é atualizada automaticamente.

## Changes

- `app/operator_ui/index.html`: `#conv-create-lead` button, `#conv-lead-form` with fields
- `app/operator_ui/app.js`: show/hide logic, pre-fill source from channel, submit handler
- `app/operator_ui/styles.css`: `.conv-lead-form` styles
- `specs/wp-147-create-lead-from-conversation.md`: spec
- `docs/operations/development-continuity.md`: updated

## Verification

- `uv run pytest`: **2016 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
