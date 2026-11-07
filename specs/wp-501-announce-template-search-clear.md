# WP-501 — Anunciar quando a busca de templates for limpa

## Objetivo

Informar operadores que usam tecnologia assistiva quando a consulta de templates
for limpa pelo botão ou pela tecla Escape.

## Escopo

- Anunciar “Busca limpa.” na região de status existente nos dois caminhos.
- Preservar filtragem, foco, API, autorização, tenant e persistência.
- Cobrir os handlers reais com dados sintéticos.
- Sem alterações de schema, migrations, integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
