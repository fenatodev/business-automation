# WP-105 — Triagem em massa de oportunidades

**Branch:** `wp/105-bulk-triage`
**Depende de:** WP-104 (main)

## Problema

O operador só podia triar uma oportunidade de cada vez, clicando em cada item e selecionando a ação. Quando um lote de oportunidades chega do mesmo canal, isso exige muitas interações repetitivas.

## Solução

Novo endpoint `POST /opportunities/bulk-triage` que aceita múltiplos IDs e aplica a mesma ação de triagem de uma vez. UI com checkboxes na lista de oportunidades e barra de triagem em massa com seletor de ação, nota opcional e botão aplicar.

## Changes

- **`app/schemas.py`**: `OpportunityBulkTriage` schema com `opportunity_ids` (1-100), `next_action` e `triage_note` opcional
- **`app/routers/opportunities.py`**: `POST /opportunities/bulk-triage` tenant-isolado; retorna `updated`, `updated_ids`, `skipped`, `next_action`
- **`app/operator_ui/index.html`**: Barra `#bulk-triage-bar` com contador, seletor de ação, campo de nota, botões aplicar/limpar
- **`app/operator_ui/app.js`**: `selectedOpportunityIds` Set; checkboxes em `showList()`; `updateBulkTriageBar()`; handler `bulk-triage-apply` e `bulk-triage-clear`
- **`app/operator_ui/styles.css`**: `.opp-item-row`, `.opp-checkbox`, `.bulk-triage-bar`, `.bulk-triage-select`, `.bulk-triage-note`
- **`tests/test_bulk_triage.py`**: 16 testes backend (ações, notas, skip, tenant isolation, auth, validação, idempotência)

## Regras

- Apenas oportunidades do tenant autenticado são atualizadas
- Oportunidades inexistentes ou de outro tenant são silenciosamente ignoradas (contadas em `skipped`)
- Máximo 100 IDs por requisição
- `triage_note` opcional; se fornecida, aplicada a todas as oportunidades atualizadas

## Verification

- **1588 testes passaram** (16 novos), 2 warnings preexistentes
- `compileall` ✓, `git diff --check` ✓
