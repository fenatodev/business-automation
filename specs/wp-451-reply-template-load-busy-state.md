# WP-451 — Anunciar carga da lista de templates

## Objetivo

Informar tecnologia assistiva enquanto a lista de templates de resposta está
sendo consultada.

## Escopo

- Definir `aria-busy="true"` na lista durante a consulta.
- Remover o estado ocupado após sucesso ou falha da consulta atual.
- Uma resposta antiga não pode limpar o estado de uma consulta mais recente.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
