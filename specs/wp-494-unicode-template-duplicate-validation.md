# WP-494 — Validar nomes Unicode ao duplicar templates

## Objetivo

Aceitar nomes de template que respeitem o limite de 100 pontos de código
Unicode ao duplicar, incluindo nomes com emoji.

## Escopo

- Contar pontos de código na validação do nome informado ao duplicar.
- Cobrir a aceitação de um nome sintético com 100 emoji e o envio correspondente.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
