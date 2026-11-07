# WP-490 — Ampliar normalização Unicode na busca de templates

## Objetivo

Fazer a busca local de templates ignorar marcas diacríticas Unicode fora do
bloco básico U+0300–U+036F, mantendo a mesma comparação sem acento para nome e
conteúdo.

## Escopo

- Normalizar texto pesquisado e indexado por decomposição NFD e remoção de
  caracteres Unicode da categoria Mark.
- Cobrir uma marca combinante fora do bloco básico no teste DOM sintético.
- Preservar o texto original exibido, contagem, estados da busca e ausência de
  chamadas extras à API.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
