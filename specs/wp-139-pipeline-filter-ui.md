# WP-139 — Filtro de pipeline visual no operador

**Data:** 31/10/2026
**Status:** Concluída

## Problema

A funcionalidade de pipeline summary (WP-072) foi perdida durante a consolidação da main. O operador não podia filtrar oportunidades por status visualmente usando chips clicáveis. O backend `/opportunities/pipeline-summary` já existia, mas a UI não o usava.

## Solução

Adicionados chips clicáveis de pipeline na toolbar de oportunidades. Cada chip mostra o status e a contagem atualizada via `pipeline-summary`. Ao clicar, o filtro `next_action` é aplicado à lista e paginação.

## Changes

- `app/operator_ui/index.html`: `#opp-pipeline` com 7 chips (Todas, Pendente, Acompanhar, Proposta, Em andamento, Concluída, Perdida) com contadores
- `app/operator_ui/app.js`: `oppPipelineFilter` state; `refreshList()` com `next_action` filter e `pipeline-summary` call; click listeners; disconnect cleanup; allowlist atualizada
- `app/operator_ui/styles.css`: `.opp-pipeline`, `.opp-pipeline-chip`, `.opp-pipeline-chip.active`, `.opp-pipeline-count`
- `tests/test_wp139_pipeline_filter_ui.py`: 19 testes de contrato UI
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **1972 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
