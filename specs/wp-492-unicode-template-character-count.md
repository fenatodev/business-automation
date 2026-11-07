# WP-492 — Contagem Unicode nos limites de templates

## Objetivo

Alinhar o contador de caracteres e os limites de entrada de templates com a
validação da API, que conta pontos de código Unicode.

## Escopo

- Contar pontos de código em vez de unidades UTF-16.
- Aplicar limites de 100 caracteres ao nome e 4000 ao conteúdo também após
  digitação ou colagem.
- Preservar os textos existentes e os limites exibidos no formulário.
- Cobrir emoji e os atributos dos campos com testes sintéticos.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
