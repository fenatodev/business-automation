# WP-489 — Normalizar acentos no texto de busca de templates

## Objetivo

Fazer a busca local de templates encontrar nomes e conteúdos acentuados quando
o operador digita sem acento, conforme o comportamento previsto no WP-469.

## Escopo

- Normalizar o texto exibido/salvo para comparação com a mesma regra usada na
  consulta, removendo marcas diacríticas e ignorando caixa.
- Preservar contagem, estado vazio, busca local e ausência de chamadas extras à
  API.
- Cobrir o comportamento com o teste DOM sintético existente.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh` quando presente.
