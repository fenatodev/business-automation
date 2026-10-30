# WP-083 — Gerenciamento de leads no operador

## Problema

O backend de leads possui CRUD completo (criação, listagem, atualização de status), mas o operador não tinha interface para gerenciá-los. O operador precisava usar a API diretamente para alterar status de leads.

## Solução

Seção "07 / LEADS" no painel do operador com:
- Lista de leads com nome, telefone, fonte e interesse
- Filtro por status (new, contacted, qualified, proposal, won, lost)
- Seletor de status inline para atualizar rapidamente
- Botão atualizar para recarregar a lista
- Carregamento automático ao conectar

## Changes

### Backend (app/routers/leads.py)
- `list_leads` agora aceita parâmetro opcional `status` para filtrar leads por status

### HTML (app/operator_ui/index.html)
- Seção "07 / LEADS" com painel, filtro de status e lista

### JavaScript (app/operator_ui/app.js)
- `leadApi()` com allowlist estrita (`/leads`, `/leads/{status}`)
- `refreshLeads()` carrega leads com filtro aplicado
- `renderLeads()` renderiza com `textContent`/`appendChild` (sem innerHTML)
- `updateLeadStatus()` envia PATCH para atualizar status
- `leadStatusLabels` mapeia status para labels em português
- `refreshLeads()` chamado no workspaceObserver ao conectar

### CSS (app/operator_ui/styles.css)
- `.lead-filters`, `.lead-filter-group` para filtros
- `.lead-list`, `.lead-item`, `.lead-item-header`, `.lead-item-name`, `.lead-item-details`
- `.lead-status-select` para o seletor de status

### Testes (tests/test_wp083_lead_management_ui.py)
- 28 testes: HTML (5), JavaScript (13), CSS (8), backend filter (2)

## Validação

- **1268 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-083 depende de WP-082 (PR #166). Base do PR: `wp/082-dashboard-metrics`.
