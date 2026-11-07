# WP-500 — Limpar consultas de espaços na busca de templates

## Objetivo

Permitir limpar a busca de templates quando o campo contém somente espaços,
tabs ou outros whitespace. A filtragem continua considerando esse texto vazio,
mas o controle de limpeza permanece disponível enquanto houver caracteres no
campo.

## Escopo

- Habilitar “Limpar busca” para qualquer valor não vazio no campo.
- Fazer Escape limpar também consultas compostas somente por whitespace.
- Cobrir ambos os caminhos com o handler real e dados sintéticos.
- Sem mudanças na API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
