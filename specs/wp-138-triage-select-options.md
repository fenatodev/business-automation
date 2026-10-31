# WP-138 — Opções completas no select de triagem individual

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O formulário de triagem individual (`#triage-form`) tinha apenas 4 opções no select `#next-action`: pending, follow, ignore, prepare_proposal. O backend `OpportunityTriageUpdate` suporta 7 opções (incluindo in_progress, done, lost), e o select de triagem em massa já as tinha todas. O operador não podia marcar uma oportunidade como "Em andamento", "Concluída" ou "Perdida" via triagem individual.

## Solução

Adicionadas as 3 opções faltantes (in_progress, done, lost) ao select de triagem individual em `index.html`, alinhando com o backend e com o select de triagem em massa.

## Changes

- `app/operator_ui/index.html`: adicionadas opções in_progress, done, lost ao select `#next-action`
- `tests/test_wp138_triage_select_options.py`: 15 testes de contrato UI
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **1953 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
