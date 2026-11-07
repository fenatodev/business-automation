# WP-457 — Atualizar busca após excluir template

## Objetivo

Manter a lista e o aviso de busca consistentes quando um template é excluído.

## Escopo

- Reaplicar o filtro local após uma exclusão confirmada.
- Preservar o estado vazio normal quando o último template é excluído.
- Exercitar a exclusão e a busca no handler real com DOM e API sintéticos.
- Sem mudanças na API, autorização, tenant, persistência, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
