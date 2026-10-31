# WP-111 — Criar customer manualmente via UI

**Status:** Concluída
**Branch:** `wp/111-create-customer-ui`

## Problema

O operador podia criar customers apenas convertendo leads. Não havia formulário para criar um customer manualmente.

## Solução

Formulário "Novo customer" na seção de customers com nome, telefone e e-mail. Reusa o endpoint `POST /customers` existente.

## Changes

- **`index.html`**: Botão "+ Novo customer"; formulário `create-customer-form` com nome, telefone, e-mail.
- **`app.js`**: `createCustomer()` com POST; handlers show/cancel/submit; validação nome obrigatório.
- **`tests/test_wp111_create_customer_ui.py`**: 15 testes de contrato UI.

## Verificação

- 1587 testes passaram, 15 novos.
- `compileall` ✓, `git diff --check` ✓.
