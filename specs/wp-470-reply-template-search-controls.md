# WP-470 — Associar busca de templates aos resultados

## Objetivo

Permitir que tecnologias assistivas identifiquem a lista afetada pela busca e
anunciem o status de filtragem associado ao campo.

## Escopo

- Associar o campo de busca à lista de templates por `aria-controls`.
- Associar o campo ao status de resultados por `aria-describedby`.
- Cobrir as relações no contrato estático da interface.
- Sem alterações em API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
