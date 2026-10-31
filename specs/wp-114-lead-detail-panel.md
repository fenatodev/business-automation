# WP-114 — Detalhes expandidos de lead

**Status:** Concluída
**Branch:** `wp/114-lead-detail-panel`

## Problema

O módulo de leads não tinha painel de detalhes. O operador via apenas a lista resumida sem poder ver todas as informações e conversas associadas a um lead.

## Solução

Painel de detalhes clicável seguindo o padrão do customer detail (WP-087). Ao clicar em um lead, exibe nome, telefone, fonte, interesse, data de criação e conversas associadas.

## Changes

- **`index.html`**: `lead-detail` panel com header, info e conversas.
- **`app.js`**: `showLeadDetail()`, `hideLeadDetail()`, click listener em `renderLeads()`.
- **`styles.css`**: `.lead-detail`, `.lead-detail-header`, `.lead-detail-info`, `.lead-conv-list`.
- **`tests/test_wp114_lead_detail_ui.py`**: 18 testes de contrato UI.

## Verificação

- 1590 testes passaram.
- `compileall` ✓, `git diff --check` ✓.
