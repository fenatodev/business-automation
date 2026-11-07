# WP-484 — Proteger template em edição contra duplicação

## Objetivo

Evitar que a duplicação de um template descarte silenciosamente o rascunho
visível ao clonar a versão carregada anteriormente.

## Escopo

- Desabilitar “Duplicar” apenas no template atualmente em edição.
- Ignorar chamadas enfileiradas para duplicá-lo enquanto a edição estiver ativa.
- Reabilitar a ação ao cancelar ou salvar a edição.
- Cobrir o fluxo com DOM e API sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
