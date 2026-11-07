# WP-454 — Anunciar o resultado da exclusão de templates

## Objetivo

Informar ao operador e à tecnologia assistiva se a exclusão de um template de
resposta foi concluída.

## Escopo

- Anunciar sucesso e falha genérica na região de status existente.
- Preservar confirmação, bloqueio contra exclusão duplicada, estado vazio e
  notificações atuais.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
