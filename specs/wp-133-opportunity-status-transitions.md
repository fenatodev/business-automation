# WP-133 — Validação de transições de status de oportunidades

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O endpoint de triagem permitia qualquer transição de status, incluindo transições inválidas como done → pending ou lost → in_progress, quebrando o ciclo F2.

## Solução

Adicionado `_VALID_TRANSITIONS` definindo as transições válidas do ciclo F2:
- pending → ignore, follow, prepare_proposal, in_progress
- follow → pending, ignore, prepare_proposal, in_progress
- prepare_proposal → pending, follow, in_progress
- in_progress → done, lost
- ignore, done, lost → estados terminais (sem saída)

Bulk triage pula oportunidades com transição inválida, reportando-as como skipped.

## Changes

- `app/routers/opportunities.py`: `_VALID_TRANSITIONS`, validação em `triage_opportunity` e `bulk_triage_opportunities`
- `tests/test_opportunity_status_transitions.py`: 11 testes novos
- `tests/test_bulk_triage.py`: ajustes para seguir transições válidas
- `tests/test_opportunity_archive.py`: ajustes para seguir transições válidas
- `tests/test_opportunity_search.py`: ajustes para seguir transições válidas
- `tests/test_opportunity_sort_pagination.py`: ajustes para seguir transições válidas

## Verification

- `uv run pytest`: **1874 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
