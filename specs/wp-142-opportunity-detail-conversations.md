# WP-142 — Conversas relacionadas à oportunidade

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O painel de detalhes da oportunidade não mostrava as conversas da mesma company, impedindo o operador de ver o contexto comunicacional antes de tomar decisões de triagem.

## Solução

Adicionado endpoint `GET /opportunities/{id}/conversations` que retorna até 50 conversas da mesma company que a oportunidade, ordenadas por ID descendente. A UI exibe uma seção "Conversas relacionadas" no painel de detalhes, com itens clicáveis que navegam para a seção de conversas.

## Changes

- `app/routers/opportunities.py`: novo endpoint `/conversations` tenant-isolado
- `app/operator_ui/index.html`: `#opp-conv-section` com `#opp-conv-list`
- `app/operator_ui/app.js`: `loadOpportunityConversations()`, allowlist atualizada
- `app/operator_ui/styles.css`: `.opp-conv-section`, `.opp-conv-item`
- `tests/test_opportunity_conversations.py`: 8 testes backend
- `specs/wp-142-opportunity-detail-conversations.md`: spec
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **1999 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
