# WP-112 — Criar lead manualmente via UI

**Status:** Concluída
**Branch:** `wp/112-create-lead-ui`

## Problema

O operador não podia criar leads manualmente; leads só entravam via pipeline n8n/intake.

## Solução

Formulário "Novo lead" na seção de leads com nome, telefone, fonte e interesse. Reusa `POST /leads` existente.

## Changes

- **`index.html`**: Botão "+ Novo lead"; formulário com nome, telefone, fonte, interesse.
- **`app.js`**: `createLead()` com POST; handlers show/cancel/submit; source default "manual".
- **`tests/test_wp112_create_lead_ui.py`**: 17 testes de contrato UI.

## Verificação

- 1589 testes passaram, 17 novos.
- `compileall` ✓, `git diff --check` ✓.
