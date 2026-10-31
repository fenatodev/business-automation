# WP-113 — Notas em oportunidades

**Status:** Concluída
**Branch:** `wp/113-opportunity-notes`

## Problema

O operador só podia salvar notas de triagem junto com a ação de triagem. Não havia forma de adicionar ou editar uma nota independentemente.

## Solução

1. `triage_note` adicionado ao `OpportunityUpdate` schema (campo já existe no banco).
2. `PATCH /opportunities/{id}` com `model_dump(exclude_unset=True)` para suporte a nulo explícito e rejeição de corpo vazio.
3. UI: painel "Nota de triagem" standalone com textarea e botão "Salvar nota" no painel de detalhes.

## Changes

- **`schemas.py`**: `triage_note` em `OpportunityUpdate`.
- **`opportunities.py`**: PATCH com `exclude_unset`, validação de corpo vazio (400).
- **`index.html`**: `opp-note-panel` com textarea e botão.
- **`app.js`**: `save-opp-note` handler; `opp-note` populado em `selectOpportunity`.
- **`styles.css`**: `.opp-note-panel` styles.
- **`tests/test_opportunity_note.py`**: 8 testes backend.
- **`tests/test_wp113_opportunity_note_ui.py`**: 13 testes UI.
- **`tests/test_opportunity_edit.py`**: `test_update_empty_body_rejected` ajustado.

## Verificação

- 1593 testes passaram.
- `compileall` ✓, `git diff --check` ✓.
