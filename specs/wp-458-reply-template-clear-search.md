# WP-458 — Limpar busca de templates de resposta

## Objetivo

Permitir que o operador limpe a busca de templates com um controle explícito.

## Escopo

- Adicionar um botão que limpa o campo e restaura a lista completa.
- Desabilitar o botão quando não há busca ativa e devolver foco ao campo ao limpar.
- Exercitar a ação pelo handler real com DOM sintético.
- Sem mudanças na API, autorização, tenant, persistência, integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
