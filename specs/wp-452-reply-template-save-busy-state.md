# WP-452 — Anunciar o salvamento de templates de resposta

## Objetivo

Informar ao operador e à tecnologia assistiva enquanto um template de resposta
está sendo salvo.

## Escopo

- Exibir um estado acessível de salvamento durante a requisição.
- Marcar o estado ocupado enquanto salva e limpar após sucesso ou falha.
- Preservar o bloqueio contra envios duplicados e os avisos existentes.
- Exercitar o handler real com DOM e API sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
