# WP-475 — Limpar busca de templates com Escape

## Objetivo

Permitir que o operador remova rapidamente o filtro da lista de templates de
resposta usando a tecla `Escape` enquanto o campo de busca está focado.

## Escopo

- Ao pressionar `Escape` com busca não vazia, limpar o campo e atualizar lista,
  contador/estado e botão de limpeza pelo filtro existente.
- Não interceptar `Escape` quando a busca já estiver vazia nem outras teclas.
- Cobrir o handler real com DOM sintético.
- Sem alterações de API, autorização, tenant, schema, persistência ou integração.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
