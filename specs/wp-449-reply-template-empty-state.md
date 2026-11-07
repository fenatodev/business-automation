# WP-449 — Estado vazio após excluir o último template

## Objetivo

Manter a lista de templates de resposta compreensível quando o operador exclui
seu último item.

## Escopo

- Exibir “Nenhum template salvo.” quando uma exclusão bem-sucedida deixar a
  lista vazia.
- Não exibir o estado vazio enquanto ainda houver templates.
- Preservar o estado da lista em caso de falha ou cancelamento.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
