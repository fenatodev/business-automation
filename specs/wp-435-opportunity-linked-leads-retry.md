# WP-435 — Retry de leads relacionados à oportunidade

## Objetivo

Permitir que o operador recupere a lista de leads relacionados quando a
consulta falhar, sem reabrir ou selecionar novamente a oportunidade.

## Escopo

- Exibir carregamento e falha em estado acessível e mensagem genérica.
- Mostrar retry somente após falha e desabilitá-lo durante a consulta.
- Repetir somente o GET da oportunidade selecionada.
- Ignorar respostas após troca de seleção ou sessão.
- Testar o handler real com DOM e API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
