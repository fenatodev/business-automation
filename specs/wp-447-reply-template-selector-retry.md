# WP-447 — Retry do seletor de templates de resposta

## Objetivo

Permitir que o operador tente novamente carregar templates quando a consulta
do seletor de resposta falhar.

## Escopo

- Anunciar o estado de carregamento e uma falha genérica acessível.
- Exibir retry somente após falha; ocultá-lo durante carregamento e após sucesso.
- Preservar as opções já carregadas em caso de falha e ignorar respostas antigas.
- Testar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
