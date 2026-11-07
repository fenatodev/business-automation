# WP-440 — Retry do ProposalBrief da oportunidade

## Objetivo

Permitir que o operador recupere o ProposalBrief da oportunidade selecionada
após uma falha de leitura, sem precisar selecionar a oportunidade novamente.

## Escopo

- Exibir retry somente após falha de consulta; escondê-lo durante nova tentativa.
- Repetir somente o GET do ProposalBrief da oportunidade selecionada.
- Ignorar resultado/finalização de seleção ou sessão obsoleta.
- Tratar 404 como ausência de brief, sem oferecer retry.
- Cobrir falha, retry bem-sucedido e sessão obsoleta com DOM/API sintéticos.
- Sem mudanças de API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
