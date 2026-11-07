# WP-478 — Proteger edição de template durante salvamento

## Objetivo

Evitar que um salvamento em andamento perca o rascunho de edição por meio do
botão de cancelar ou da tecla `Escape`.

## Escopo

- Desabilitar cancelar edição enquanto a requisição de salvamento está ativa.
- Ignorar cancelamento por clique e `Escape` durante esse período.
- Reabilitar o botão após sucesso ou falha, preservando o fluxo atual.
- Cobrir os handlers reais com API e DOM sintéticos.
- Sem alterações de API, autorização, tenant, persistência, schema ou
  integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
