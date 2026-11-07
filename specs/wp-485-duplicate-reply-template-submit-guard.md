# WP-485 — Evitar duplicação concorrente de templates

## Objetivo

Impedir que cliques repetidos em templates diferentes criem duplicatas simultâneas e concorrentes.

## Escopo

- Desabilitar todas as ações de duplicação enquanto uma cópia está sendo criada.
- Ignorar chamadas enfileiradas durante a operação ativa.
- Restaurar os botões ao concluir, preservando o bloqueio do template em edição.
- Cobrir o fluxo com DOM e API sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
