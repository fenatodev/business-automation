# WP-506 — Preservar rascunho ao abrir resposta

## Objetivo

Evitar que a sugestão automática substitua texto que o operador já escreveu ao
reabrir o formulário de resposta.

## Escopo

- Solicitar sugestão automática somente quando o campo de resposta estiver vazio.
- Preservar a sugestão automática e a limpeza do aviso de template quando o
  campo estiver vazio.
- Cobrir os handlers reais com DOM e resposta HTTP sintéticos.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
