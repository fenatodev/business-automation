# WP-439 — Retry da timeline da oportunidade

## Objetivo

Permitir que o operador recupere as atividades da oportunidade selecionada
após uma falha de leitura, sem precisar selecioná-la novamente.

## Escopo

- Anunciar carregamento e falha em estado acessível com mensagem genérica.
- Mostrar retry somente após falha e desabilitá-lo durante a consulta.
- Repetir apenas o GET da timeline da oportunidade selecionada.
- Ignorar sucesso, falha ou finalização de respostas de seleção/sessão obsoletas.
- Testar falha, retry bem-sucedido e corridas com DOM/API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
