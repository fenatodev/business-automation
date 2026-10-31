# WP-087 — Visão detalhada de customer com conversas

## Problema

O operador pode ver a lista de customers (WP-086) mas não consegue ver os
detalhes de um customer específico nem suas conversas associadas. O backend
possui `GET /customers/{customer_id}` e o modelo `Conversation` tem `customer_id`
como FK, mas o endpoint de conversas não aceitava filtro por `customer_id`.

## Solução

### Backend

- `GET /companies/{company_id}/conversations` aceita parâmetro opcional
  `customer_id` para filtrar conversas por customer
- `GET /companies/{company_id}/conversations/count` também aceita `customer_id`
- Tenant isolation preservado via `require_operator_company`

### UI

- Clicar em um customer na lista abre o painel de detalhes
- Painel mostra nome, telefone, email e lead de origem
- Lista as conversas associadas ao customer (canal + status)
- Botão "← Voltar" retorna à lista
- Renderização com `textContent`/`appendChild` (sem innerHTML)

## Changes

- `app/routers/conversations.py`: filtro `customer_id` em list e count
- `app/operator_ui/index.html`: seção `#customer-detail` com back, info e conversas
- `app/operator_ui/app.js`: `showCustomerDetail()`, `hideCustomerDetail()`,
  `loadCustomerConversations()`, click handler em customer items
- `app/operator_ui/styles.css`: `.customer-detail`, `.customer-conv-item`, etc.
- `tests/test_wp087_customer_detail.py`: 26 testes (backend, HTML, JS, CSS)

## Validação

- **1349 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-087 depende de WP-086 (PR #170). Base do PR: `wp/086-customer-list-ui`.
