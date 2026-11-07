# WP-482 — Confirmar cancelamento da edição de template

## Objetivo

Informar ao operador quando o cancelamento da edição de um template foi concluído.

## Escopo

- Após cancelamento confirmado (ou sem alterações), anunciar “Edição cancelada.”
  no estado acessível já usado pelo formulário.
- Se o operador recusar o descarte, preservar os valores e a mensagem/estado atual.
- Cobrir cancelamento pelo botão e pelo comportamento compartilhado com Escape.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
