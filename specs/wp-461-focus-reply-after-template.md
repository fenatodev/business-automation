# WP-461 — Devolver foco ao rascunho após inserir template

## Objetivo

Manter o fluxo de digitação no campo de resposta após escolher um template.

## Escopo

- Após inserir conteúdo válido de template e posicionar o cursor, focar o campo
  de resposta para que a digitação seguinte continue no rascunho.
- Cobrir o handler real com DOM sintético, incluindo foco e posição do cursor.
- Sem alterações na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
