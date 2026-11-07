# WP-431 — Retry de conversas no detalhe da oportunidade

## Objetivo

Permitir que o operador recupere a lista de conversas ligadas à oportunidade
selecionada quando uma consulta falhar, sem reabrir ou selecionar novamente o
registro.

## Escopo

- Informar carregamento, sucesso/falha e busy state acessíveis.
- Mostrar retry apenas após falha; durante a consulta ele fica desabilitado.
- Repetir somente o GET da oportunidade ainda selecionada.
- Ignorar resposta de uma seleção antiga.
- Testar o handler real com DOM e API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
