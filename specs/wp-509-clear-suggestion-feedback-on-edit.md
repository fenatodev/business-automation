# WP-509 — Limpar aviso de sugestão ao editar resposta

## Objetivo

Ao começar a escrever uma resposta manual, limpar o aviso de indisponibilidade
ou falha da sugestão automática. O feedback deixa de ocupar a área de status
quando o operador já está seguindo com uma resposta própria.

## Escopo e limites

- Conectar a limpeza ao evento de edição do campo de resposta existente.
- Cobrir o handler real com teste JavaScript sintético.
- Preservar o comportamento existente de limpeza do aviso de inserção de template.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
