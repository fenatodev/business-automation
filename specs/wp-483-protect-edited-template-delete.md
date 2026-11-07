# WP-483 — Proteger template em edição contra exclusão

## Objetivo

Evitar que a exclusão de um template descarte o rascunho que está sendo editado.

## Escopo

- Desabilitar a ação de exclusão apenas do template atualmente em edição.
- Ignorar chamadas enfileiradas para excluir esse template enquanto a edição estiver ativa.
- Reabilitar a exclusão ao cancelar ou salvar a edição.
- Cobrir o fluxo com DOM e API sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
