# WP-495 — Focar o template recém-duplicado

## Objetivo

Após duplicar um template com sucesso, mover o foco para a ação “Editar” do
novo item para que o operador continue a partir do resultado criado.

## Escopo

- Identificar o item criado pelo ID retornado pela API e focar seu botão de edição.
- Cobrir o foco no item novo e confirmar que não retorna ao botão da origem.
- Sem mudanças de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
