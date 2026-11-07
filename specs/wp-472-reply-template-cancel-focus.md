# WP-472 — Devolver foco ao cancelar edição de template

## Objetivo

Manter a navegação por teclado na lista de templates após cancelar uma edição.

## Escopo

- Guardar o botão “Editar” que iniciou a edição.
- Ao cancelar, limpar o formulário e devolver o foco a esse botão se ele ainda
  estiver conectado ao documento; caso contrário, focar o campo de nome.
- Cobrir o comportamento com DOM sintético pelo handler real.
- Sem alterações na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
