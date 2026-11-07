# WP-487 — Resetar o estado da busca quando a lista de templates fica vazia

## Objetivo

Evitar que a interface mantenha uma contagem de busca antiga ou um botão
“Limpar busca” habilitado depois que a recarga da lista retorna zero templates.

## Escopo

- Reaplicar o filtro local ao renderizar o estado vazio, limpando a contagem e
  desabilitando “Limpar busca” quando não há itens.
- Cobrir o caso com lista anteriormente populada e busca ativa usando DOM
  sintético.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
