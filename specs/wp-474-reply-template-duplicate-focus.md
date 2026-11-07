# WP-474 — Devolver foco após duplicar template

## Objetivo

Manter a navegação por teclado na lista de templates após uma duplicação bem-sucedida.

## Escopo

- Identificar cada item da lista pelo ID do template.
- Após criar a cópia, atualizar a lista e o seletor, então devolver o foco ao botão “Duplicar” do template original.
- Cobrir o comportamento pelo handler real com DOM e API sintéticos.
- Sem alterações na API, autorização, tenant, schema, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
