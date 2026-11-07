# WP-466 — Validar campos em branco nos templates de resposta

## Objetivo

Dar retorno claro quando nome ou conteúdo contiver apenas espaços em branco.

## Escopo

- Informar no estado acessível existente que nome e conteúdo são obrigatórios.
- Focar o primeiro campo inválido, priorizando nome.
- Não enviar requisição nem limpar os valores nesse caso.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
