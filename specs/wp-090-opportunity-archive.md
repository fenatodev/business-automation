# WP-090 — Arquivamento visual de oportunidades

## Problema

O operador não pode ocultar oportunidades finalizadas (done/lost) da lista
principal, poluindo a visão de trabalho ativo.

## Solução

### Backend

- `GET /opportunities` aceita `exclude_archived=true` para filtrar
  oportunidades com `next_action` em `["done", "lost"]`
- `OpportunityTriageUpdate` inclui `in_progress`, `done`, `lost` como
  opções válidas de triagem
- Tenant isolation preservado via `require_operator`

### UI

- Toggle "Exibir arquivadas" ao lado do contador de oportunidades
- Desmarcado por padrão — oculta done/lost
- Atualiza a lista automaticamente ao mudar o toggle

## Changes

- `app/schemas.py`: `in_progress`, `done`, `lost` no triage Literal
- `app/routers/opportunities.py`: `exclude_archived` query param
- `app/operator_ui/index.html`: toolbar com toggle checkbox
- `app/operator_ui/app.js`: `refreshList()` com filtro; change listener
- `app/operator_ui/styles.css`: `.opp-toolbar`, `.opp-archive-toggle`
- `tests/test_opportunity_archive.py`: 16 testes (backend + UI contract)

## Validação

- **1393 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-090 depende de WP-089 (PR #173). Base do PR: `wp/089-create-conversation-from-customer`.
