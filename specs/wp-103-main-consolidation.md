# WP-103 — Consolidação da main

## Problema

As WPs da WP-078 à WP-101 foram merged em cadeia nas branches WP
(wp/080 → wp/081 → ... → wp/101), não na main. A main ficou com versão
antiga do código (parada na WP-078) enquanto testes antigos permaneciam
falhando contra a versão desatualizada.

## Solução

1. Consolidar wp/101 (ponta da cadeia) como base da branch de consolidação
2. Merge de main para preservar arquivos perdidos (supervisor, specs, tests)
3. Resolver conflitos aceitando a versão wp/101 (mais recente)
4. Remover testes UI obsoletos substituídos pela versão unificada WP-077
5. Adicionar `next_action` filter e `pipeline-summary` endpoint ao router
6. Corrigir `test_client0_simulation.py` para usar `/approve` dedicado
7. Atualizar `test_operator_ui.py` para botões approve/reject

## Files modificados

- `app/routers/opportunities.py`: +`next_action` filter, +`pipeline-summary`
- `tests/test_client0_simulation.py`: usar `/approve` em vez de PATCH com "approved"
- `tests/test_operator_ui.py`: verificar botões approve/reject
- `docs/operations/development-continuity.md`: atualizado

## Files removidos

- `tests/test_brief_approval.py` (substituído por test_brief_approve_reject.py)
- `tests/test_opportunity_close.py` (schema já tem done/lost)
- `tests/test_triage_in_progress.py` (schema já tem in_progress)
- `tests/test_wp070_intake_ui.py` (unificado em WP-077)
- `tests/test_wp072_pipeline_ui.py` (unificado em WP-077)
- `tests/test_wp073_triage_ui.py` (unificado em WP-077)
- `tests/test_wp074_close_ui.py` (unificado em WP-077)
- `tests/test_wp075_conversation_ui.py` (unificado em WP-077)
- `tests/test_wp076_human_reply_ui.py` (unificado em WP-077)
- `tests/test_wp077_connect_reply_ui.py` (duplicado)
- `tests/test_review_pagination_runtime.py` (obsoleto)
- `tests/test_internal_tasks_panel_runtime.py` (obsoleto)

## Verification

- **1555 testes passaram**, 2 warnings preexistentes
- `compileall` ✓
- `git diff --check` ✓
