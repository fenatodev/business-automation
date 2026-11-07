# WP-496 — Focar template duplicado fora do filtro atual

## Objetivo

Ao duplicar um template enquanto a busca está ativa, permitir que o botão
“Editar” do novo item receba foco mesmo quando o nome sugerido não corresponde
ao filtro atual.

## Escopo

- Limpar a busca somente quando o item recém-criado estiver oculto pelo filtro.
- Manter filtros que já exibem o novo item e focar seu botão “Editar”.
- Cobrir o caso com busca e dados sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
