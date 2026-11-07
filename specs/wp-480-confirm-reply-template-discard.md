# WP-480 — Confirmar descarte de edição de template

## Objetivo

Evitar descartar silenciosamente alterações não salvas ao cancelar uma edição
de template de resposta.

## Escopo

- Solicitar confirmação ao cancelar quando nome ou conteúdo diferir do original.
- Aplicar a mesma confirmação ao botão Cancelar e à tecla Escape.
- Permitir cancelar sem confirmação quando não houver alterações.
- Se o operador recusar, preservar valores, edição e foco no formulário.
- Cobrir os comportamentos com DOM sintético.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
