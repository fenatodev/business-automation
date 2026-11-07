# WP-486 — Preservar proteções da edição após duplicar template

## Objetivo

Manter protegida a linha de um template em edição quando a duplicação de outro
template recarrega a lista.

## Escopo

- Após recarregar a lista por uma duplicação, reaplicar os bloqueios de editar,
  excluir e duplicar na linha atualmente em edição.
- Preservar os valores do rascunho e deixar os outros templates operáveis.
- Cobrir o fluxo com DOM e API sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
