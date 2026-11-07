# WP-479 — Proteger rascunho ao trocar template em edição

## Objetivo

Evitar que selecionar “Editar” em outro template substitua silenciosamente as
alterações ainda não salvas no formulário atual.

## Escopo

- Desabilitar as ações de edição da lista enquanto há um template em edição.
- Ignorar chamadas enfileiradas que tentem iniciar outra edição nesse estado.
- Reabilitar as ações após cancelar ou concluir com sucesso.
- Cobrir início, troca bloqueada, cancelamento e salvamento com DOM/API sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
