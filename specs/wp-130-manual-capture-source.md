# WP-130 — Fonte configurável na captura manual de oportunidades

**Data:** 31/10/2026
**Status:** Em desenvolvimento

## Problema

O formulário de captura manual de oportunidades tinha a fonte hardcodeada como "99freelas", tornando-o inútil para operadores de outras companies que não usam essa plataforma.

## Solução

Adicionar um seletor de fonte no formulário de captura manual, permitindo escolher entre:
- Captura manual (padrão)
- 99Freelas
- Intake comercial
- Review queue

## Changes

- `app/schemas.py`: `"manual"` adicionado ao `OpportunityCreate.source` Literal
- `app/operator_ui/index.html`: Dropdown de fonte no formulário de captura
- `app/operator_ui/app.js`: Usar a fonte selecionada em vez de "99freelas" fixo

## Testes

- Testes de contrato UI para verificar o dropdown de fonte
- Testes backend para validar fonte "manual" no OpportunityCreate

## Verification

- `uv run pytest`: todos passando
- `compileall` ✓
- `git diff --check` ✓
