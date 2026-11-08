# WP-511 — Feedback durante sugestão automática de resposta

## Objetivo

Informar ao operador que a sugestão automática de resposta está sendo gerada,
usando a região acessível de status já presente no formulário.

## Escopo e limites

- Anunciar “Gerando sugestão...” enquanto a solicitação automática estiver
  pendente.
- Limpar o estado quando uma sugestão válida for aplicada; erros e edição
  manual mantêm seus comportamentos existentes.
- Cobrir o handler real com chamadas sintéticas controladas.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
