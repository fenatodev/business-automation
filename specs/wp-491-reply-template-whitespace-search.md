# WP-491 — Normalizar espaços na busca de templates

## Objetivo

Permitir que a busca local de templates encontre texto mesmo quando a consulta
e o conteúdo usam espaços, tabs ou quebras de linha diferentes.

## Escopo

- Colapsar sequências de whitespace em um espaço, além da normalização de caixa
  e marcas Unicode já existente, tanto na consulta quanto no texto indexado.
- Preservar o conteúdo original exibido, contagem, estados da busca e ausência
  de chamadas extras à API.
- Cobrir whitespace misto com DOM sintético e o handler real.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
