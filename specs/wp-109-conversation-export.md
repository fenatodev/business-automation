# WP-109 — Exportação CSV de conversas

**Status:** Concluída
**Branch:** `wp/109-conversation-export`

## Problema

O operador podia exportar oportunidades, leads e customers (WP-106), mas não conversas.

## Solução

`GET /companies/{company_id}/conversations/export.csv` retorna CSV tenant-isolado com todas as conversas e mensagens. Botão "Exportar CSV" na seção de conversas.

## Changes

### Backend

- **`conversations.py`**: `GET /companies/{company_id}/conversations/export.csv` — CSV com ID, Canal, Status, Lead, Customer, Mensagens (concatenadas com `[sender_type]`), Criado em.

### UI

- **`index.html`**: Botão "Exportar CSV" ao lado de "Atualizar".
- **`app.js`**: Handler com download via blob; allowlist atualizada.
- Empresa derivada de `opportunities[0].company_id` (padrão existente).

### Testes

- **`tests/test_conversation_export.py`**: 7 testes (básico, vazio, tenant isolation, auth, campos, mensagens, company not found).

## Verificação

- 1579 testes passaram, 2 warnings preexistentes.
- `compileall` ✓, `git diff --check` ✓.
