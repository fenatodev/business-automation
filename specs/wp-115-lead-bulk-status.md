# WP-115 — Status em massa de leads

**Status:** Concluída
**Branch:** `wp/115-lead-bulk-status`

## Problema

O operador só podia alterar o status de um lead de cada vez. Com muitos leads, isso era trabalhoso.

## Solução

`POST /leads/bulk-status` aceita 1-100 IDs e aplica o mesmo status tenant-isolado. UI com checkboxes e barra de status em massa.

## Changes

- **`schemas.py`**: `LeadBulkStatus` com `lead_ids` (1-100) e `status`.
- **`leads.py`**: `POST /leads/bulk-status` tenant-isolado.
- **`index.html`**: Barra `leads-bulk-bar` com contador, seletor e botões.
- **`app.js`**: Checkboxes, `selectedLeadIds`, `updateLeadsBulkBar()`, handlers apply/clear.
- **`styles.css`**: `.leads-bulk-bar`, `.lead-checkbox`.
- **`tests/test_lead_bulk_status.py`**: 8 testes backend.

## Verificação

- 1580 testes passaram.
- `compileall` ✓, `git diff --check` ✓.
