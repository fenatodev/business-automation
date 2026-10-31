# WP-108 — Painel de detalhes da oportunidade

**Status:** Concluída
**Branch:** `wp/108-opportunity-detail-panel`

## Problema

O operador não podia ver o proposal brief associado quando a opportunity estava em status diferente de `prepare_proposal` (ex: `in_progress`, `done`, `lost`). Além disso, o painel de seleção não exibia metadados importantes como fonte, data de captura e nota de triagem.

## Solução

1. `selectOpportunity()` agora sempre tenta carregar o brief associado, independentemente do status da opportunity.
2. Adicionados campos de metadados: fonte (source), capturada em (captured_at) e nota de triagem (triage_note).
3. Botão "Ver brief" rola suavemente até o painel do brief.

## Changes

### UI

- **`index.html`**: Campos `selected-source`, `selected-captured-at`, `selected-triage-note` no metadata dl; botão `view-brief-button` em `opp-detail-actions`.
- **`app.js`**: `selectOpportunity()` sempre chama `loadBrief()`; populate dos novos campos; `clearSelection()` limpa os novos campos; handler do botão "Ver brief" com `scrollIntoView`.
- **`styles.css`**: `.opp-detail-actions` com layout flex.

### Testes

- **`tests/test_wp108_opportunity_detail.py`**: 18 testes de contrato UI (HTML elements, JS behavior, CSS styles, metadata order).

## Segurança

- Nenhuma mudança de backend.
- O brief é carregado via endpoint existente `GET /opportunities/{id}/proposal-brief` (já tenant-isolado).
- Se o brief não existir, o painel exibe "Ainda não criado" (comportamento existente).

## Verificação

- 1590 testes passaram, 2 warnings preexistentes.
- `compileall` ✓, `git diff --check` ✓.
