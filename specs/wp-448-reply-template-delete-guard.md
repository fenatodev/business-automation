# WP-448 — Evitar exclusões duplicadas de templates

## Objetivo

Impedir que cliques repetidos em Excluir enviem requisições concorrentes para o
mesmo template.

## Escopo

- Ignorar novos cliques enquanto a exclusão estiver em andamento.
- Desabilitar o botão após confirmação e reabilitá-lo após sucesso ou falha.
- Preservar confirmação, notificações e remoção da linha após sucesso.
- Exercitar o handler real com API e DOM sintéticos, incluindo sucesso, falha e
  cancelamento da confirmação.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh` quando disponível.
