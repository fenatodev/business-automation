# WP-469 — Buscar templates sem exigir acentuação

## Objetivo

Permitir encontrar templates digitando letras sem acento quando o conteúdo
salvo tem acentos, mantendo a busca local existente.

## Escopo

- Normalizar query e texto dos templates removendo marcas diacríticas.
- Manter a busca case-insensitive, contagem e estado vazio existentes.
- Exercitar o filtro real com DOM sintético, incluindo `saudacao` para
  encontrar `Saudação`.
- Sem chamadas adicionais à API ou mudanças em autorização, tenant,
  persistência, integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
