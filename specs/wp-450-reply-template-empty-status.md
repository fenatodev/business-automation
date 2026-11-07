# WP-450 — Anunciar a lista vazia de templates

## Objetivo

Anunciar para tecnologia assistiva quando não há templates de resposta salvos.

## Escopo

- Marcar a mensagem “Nenhum template salvo.” como `role="status"` tanto no
  carregamento vazio quanto após a exclusão bem-sucedida do último template.
- Preservar o texto e o comportamento atual da lista.
- Exercitar os handlers reais com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
