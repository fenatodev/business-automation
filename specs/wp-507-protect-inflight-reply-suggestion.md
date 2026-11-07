# WP-507 — Proteger rascunho de sugestão em voo

## Objetivo

Evitar que uma sugestão automática atrasada sobrescreva texto digitado pelo
operador ou seja aplicada a outra conversa depois que a chamada começou.

## Escopo

- Aplicar a sugestão automática somente se o formulário continuar aberto, a
  conversa selecionada continuar a mesma e o campo de resposta continuar vazio.
- Cobrir o handler real com respostas HTTP sintéticas e chamadas assíncronas
  controladas.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
