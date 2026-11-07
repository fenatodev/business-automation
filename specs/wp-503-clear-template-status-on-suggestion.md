# WP-503 — Limpar aviso de template ao copiar sugestão

## Objetivo

Evitar que o aviso de inserção de template permaneça visível depois que uma
sugestão de resposta substitui o rascunho no formulário.

## Escopo

- Limpar o aviso de inserção ao copiar uma sugestão para o formulário.
- Preservar o conteúdo copiado, a abertura do formulário e a notificação atual.
- Cobrir o handler real com DOM sintético.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh` quando presente.
