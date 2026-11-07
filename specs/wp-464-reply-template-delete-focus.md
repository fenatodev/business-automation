# WP-464 — Preservar foco após excluir template de resposta

## Objetivo

Manter a navegação por teclado na lista de templates após uma exclusão.

## Escopo

- Após uma exclusão bem-sucedida, focar o botão de exclusão do próximo template
  visível.
- Quando não houver outro template visível, focar o campo de busca.
- Cobrir ambos os caminhos pelo handler real com DOM sintético.
- Sem alterações na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
