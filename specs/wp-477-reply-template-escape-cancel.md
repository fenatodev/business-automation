# WP-477 — Cancelar edição de template com Escape

## Objetivo

Permitir que o operador cancele a edição de um template de resposta pela tecla
`Escape` enquanto o campo de nome ou conteúdo estiver focado.

## Escopo

- Em modo de edição, `Escape` cancela pelo mesmo fluxo do botão existente,
  limpa o formulário e restaura o foco ao item que iniciou a edição.
- Em modo de criação, `Escape` não é interceptado.
- Cobrir o handler real com DOM sintético.
- Sem alterações de API, autorização, tenant, schema, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
