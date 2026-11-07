# WP-488 — Resetar filtro após excluir o último template

## Objetivo

Manter a busca consistente quando uma exclusão deixa a lista sem templates.
A busca e o botão de limpeza não devem permanecer ativos para uma lista vazia.

## Escopo

- Ao excluir o último template, limpar o campo de busca e reaplicar o estado do filtro.
- Cobrir exclusão do último item com busca ativa em DOM sintético.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
