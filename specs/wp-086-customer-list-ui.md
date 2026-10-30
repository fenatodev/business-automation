# WP-086 — Lista de customers no operador

## Problema

O backend possui CRUD completo de customers (listagem, criação, conversão de leads),
mas o operador não tinha interface para visualizar os customers. Após converter
leads em customers (WP-085), não havia onde ver a lista de customers ativos.

## Solução

Seção "08 / CUSTOMERS" no painel do operador com:
- Lista de customers com nome, telefone, email e lead de origem
- Botão atualizar para recarregar a lista
- Carregamento automático ao conectar
- Estado vazio quando não há customers

## Changes

### HTML (app/operator_ui/index.html)
- Seção "08 / CUSTOMERS" com painel e lista

### JavaScript (app/operator_ui/app.js)
- `customerApi()` com allowlist estrita (`/customers`)
- `refreshCustomers()` carrega lista de customers
- `renderCustomers()` renderiza com `textContent`/`appendChild` (sem innerHTML)
- `refreshCustomers()` chamado no workspaceObserver ao conectar

### CSS (app/operator_ui/styles.css)
- `.customer-list`, `.customer-item`, `.customer-item-header`,
  `.customer-item-name`, `.customer-item-details`

### Testes (tests/test_wp086_customer_list_ui.py)
- Testes de contrato UI: HTML, JS, CSS

## Validação

- pytest, compileall, diff-check

## Notas

WP-086 depende de WP-085 (PR #169). Base do PR: `wp/085-lead-convert-ui`.
