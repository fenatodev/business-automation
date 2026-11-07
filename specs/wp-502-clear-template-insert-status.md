# WP-502 — Limpar o aviso de template ao editar a resposta

## Objetivo

Evitar que o aviso de inserção pareça descrever o rascunho atual depois que a
pessoa continua editando manualmente a resposta.

## Escopo

- Limpar o aviso de inserção quando o campo de resposta receber entrada manual.
- Preservar o aviso gerado pela inserção do template até a próxima edição.
- Cobrir o handler real com DOM sintético.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
