# WP-497 — Acessar template criado com busca ativa

## Objetivo

Depois de criar um template enquanto a busca está ativa, manter o item novo
acessível: limpar a busca somente se ela o ocultar e focar o botão “Editar”.
Se a busca já mostrar o item, preservá-la.

## Escopo

- Cobrir a criação com filtro incompatível e com filtro compatível usando dados
  sintéticos.
- Não alterar o comportamento de edição, API, autorização, tenant, persistência,
  schema, migrations ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
