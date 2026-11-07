# WP-499 — Restaurar foco ao cancelar edição com busca ativa

## Objetivo

Ao cancelar a edição de um template, devolver o foco ao botão “Editar”. Se a
busca tiver ocultado o template desde o início da edição, limpar o filtro antes
de focar o botão.

## Escopo

- Cobrir template visível e oculto pelo filtro usando DOM sintético.
- Não alterar criação, salvamento, API, autorização, tenant, persistência,
  schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
