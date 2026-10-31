# WP-146 — Atalhos de teclado no operador

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O operador dependia inteiramente do mouse para navegar, buscando e limpando seleção.

## Solução

Adicionados atalhos de teclado globais:
- **Ctrl+K** (ou Cmd+K): foca o campo de busca de oportunidades
- **Escape**: limpa a seleção atual e retorna à lista

Indicação dos atalhos adicionada no rodapé da interface.

## Changes

- `app/operator_ui/app.js`: `keydown` listener global com Ctrl+K e Escape
- `app/operator_ui/index.html`: hint de atalhos no footer
- `docs/operations/development-continuity.md`: atualizado

## Verification

- `uv run pytest`: **2016 passed**, 2 warnings
- `compileall` ✓
- `git diff --check` ✓
