# WP-473 — Duplicar templates de resposta

## Objetivo

Permitir criar uma cópia independente de um template existente pela interface
interna do operador.

## Escopo

- Adicionar ação “Duplicar” à lista de templates.
- Solicitar o nome da cópia, sugerindo “(cópia)” e respeitando o limite de 100
  caracteres.
- Criar novo registro com o endpoint POST existente, copiando o conteúdo;
  cancelamento e nomes inválidos não fazem requisição.
- Anunciar sucesso ou falha e atualizar a lista e o seletor após sucesso.
- Cobrir o handler real com DOM e API sintéticos.
- Sem mudanças na API, autorização, tenant, schema, persistência adicional ou
  integrações externas.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
