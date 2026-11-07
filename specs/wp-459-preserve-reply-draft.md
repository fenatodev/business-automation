# WP-459 — Preservar rascunho ao inserir template de resposta

## Objetivo

Evitar que a seleção de um template apague silenciosamente texto já escrito na
resposta manual.

## Escopo

- Inserir o conteúdo do template na posição atual do cursor.
- Substituir somente o texto selecionado, se houver; preservar todo o restante.
- Posicionar o cursor logo após o conteúdo inserido.
- Exercitar o handler real com DOM sintético para cursor, seleção, rascunho
  vazio e opção sem template selecionado.
- Sem mudanças na API, autorização, tenant, persistência, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
