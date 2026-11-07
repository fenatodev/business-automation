# WP-468 — Mostrar resultados da busca de templates

## Objetivo

Informar ao operador quantos templates correspondem à busca local.

## Escopo

- Exibir uma mensagem singular ou plural no estado acessível já existente.
- Manter o aviso de zero resultados e limpar a mensagem quando a busca não está ativa.
- Exercitar o filtro real com DOM sintético para um, vários e zero resultados.
- Sem chamadas adicionais à API ou mudanças em autorização, tenant, persistência,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
