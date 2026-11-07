# WP-498 — Manter acessível o template atualizado com busca ativa

## Objetivo

Depois de editar um template com busca ativa, manter o item atualizado acessível.
Preservar a busca se o item continuar visível; limpá-la somente se a edição
fizer o item deixar de corresponder e, em ambos os casos, focar o botão “Editar”.

## Escopo

- Cobrir atualização com filtro compatível e incompatível usando dados
  sintéticos.
- Não alterar criação, exclusão, API, autorização, tenant, persistência, schema,
  migrations ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
