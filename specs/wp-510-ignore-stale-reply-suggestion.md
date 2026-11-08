# WP-510 — Ignorar sugestão de resposta de outra conversa

## Objetivo

Impedir que a resposta de uma solicitação explícita de sugestão, iniciada em
uma conversa, apareça no painel após o operador selecionar outra conversa.

## Escopo e limites

- Conferir a conversa selecionada após a resposta HTTP e após a leitura do JSON.
- Ignorar também erros atrasados da conversa anterior.
- Cobrir o handler real com chamadas assíncronas e conteúdo sintético.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
