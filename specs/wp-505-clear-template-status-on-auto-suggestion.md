# WP-505 — Limpar aviso de template ao carregar sugestão automática

## Objetivo

Evitar que o aviso de inserção de template permaneça visível quando a sugestão
automática substitui o texto do formulário de resposta ao abri-lo.

## Escopo

- Limpar o aviso de template após uma sugestão automática bem-sucedida atualizar
  o campo de resposta.
- Manter o comportamento atual quando a sugestão não é carregada.
- Cobrir o listener real com DOM e resposta HTTP sintéticos.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
