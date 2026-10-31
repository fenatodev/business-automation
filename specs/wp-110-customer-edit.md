# WP-110 — Editar customer via UI

**Status:** Concluída
**Branch:** `wp/110-customer-edit`

## Problema

Não havia forma de editar um customer após a criação. O backend `POST /customers` criava customers, mas não existia endpoint `PATCH` para atualizar nome, telefone ou e-mail.

## Solução

1. `CustomerUpdate` schema com campos parciais opcionais (name, phone, email).
2. `PATCH /customers/{customer_id}` tenant-isolado — atualiza apenas os campos enviados.
3. UI: botão "✏️ Editar" no painel de detalhes do customer; formulário inline com campos nome, telefone, e-mail; validação de nome obrigatório.

## Changes

### Backend

- **`schemas.py`**: `CustomerUpdate` com `name`, `phone`, `email` opcionais.
- **`customers.py`**: `PATCH /customers/{customer_id}` com `model_dump(exclude_unset=True)` para atualização parcial.
- **`tests/test_customer_update.py`**: 10 testes backend (nome, telefone, email, todos campos, corpo vazio, tenant isolation, not found, auth, max length, preserve unset).

### UI

- **`index.html`**: Formulário `customer-edit-form` com inputs nome, telefone, e-mail; botões salvar/cancelar.
- **`app.js`**: `showCustomerEditForm()`, `hideCustomerEditForm()`, `updateCustomer()`; botão editar em `showCustomerDetail()`; handlers de submit e cancel.
- **`tests/test_wp110_customer_edit_ui.py`**: 16 testes de contrato UI.

## Segurança

- Tenant isolation via `_get_tenant_customer()` — operador só edita customers da própria company.
- Validação de schema com `Field(max_length=...)` para prevenir inputs excessivos.
- `exclude_unset=True` garante que campos não enviados não são alterados.

## Verificação

- 1598 testes passaram, 2 warnings preexistentes.
- `compileall` ✓, `git diff --check` ✓.
