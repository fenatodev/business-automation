# WP-443 — Feedback e retry da lista de templates de resposta

## Objetivo

Deixar explícito para o operador quando a consulta de templates falha e permitir
uma nova tentativa na própria seção de gerenciamento.

## Escopo

- Anunciar carregamento e falha com texto genérico acessível.
- Mostrar retry somente após erro; ocultá-lo durante carregamento e após sucesso.
- Preservar o conteúdo de templates existente em caso de erro e ignorar
  respostas de carregamentos substituídos.
- Testar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
