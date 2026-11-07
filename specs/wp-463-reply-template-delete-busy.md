# WP-463 — Estado ocupado ao excluir template de resposta

## Objetivo

Informar o operador enquanto a exclusão de um template está em andamento.

## Escopo

- Anunciar “Excluindo template” na região de status enquanto a requisição DELETE aguarda resposta.
- Preservar as mensagens existentes de sucesso e falha e o bloqueio contra exclusão duplicada.
- Exercitar o estado pendente pelo handler real com DOM e API sintéticos.
- Sem mudanças na API, autorização, tenant, persistência, integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
