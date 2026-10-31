# WP-156 — Exibir orçamento e descrição na lista de oportunidades

## Problema

A lista de oportunidades mostrava apenas `#id · título` e badge de status. O operador não podia ver o orçamento estimado, prazo ou descrição sem abrir cada oportunidade individualmente.

## Solução

`renderList()` em `app.js` agora exibe:
1. **Linha de título**: `#id · título` + badge de status (flex row)
2. **Descrição truncada**: até 120 caracteres com reticências
3. **Linha de metadados**: orçamento (💰) e prazo (📅) quando presentes

## Mudanças

- `app/operator_ui/app.js`: `renderList()` com `opp-item-title-row`, `opp-item-description`, `opp-item-meta`
- `app/operator_ui/styles.css`: estilos `.opp-item-title-row`, `.opp-item-description`, `.opp-item-meta`, `.opp-item-budget`, `.opp-item-deadline`
- `tests/test_wp156_opportunity_list_budget.py`: 16 testes de contrato UI

## Regras

- Sem `innerHTML`; tudo via `textContent`/`createElement` (regra XSS)
- Descrição truncada a 120 caracteres
- Metadados só aparecem se budget ou deadline existirem
- Sem mudança no backend

## Verificação

- 2091 testes passaram (16 novos)
- `compileall` ✓, `git diff --check` ✓
