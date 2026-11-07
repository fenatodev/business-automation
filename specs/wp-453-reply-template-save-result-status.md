# WP-453 — Anunciar o resultado do salvamento de templates

## Objetivo

Manter o operador e a tecnologia assistiva informados após o salvamento de um
template de resposta.

## Escopo

- Anunciar sucesso no estado acessível existente após a API confirmar a criação.
- Anunciar uma falha genérica sem expor detalhes internos.
- Limpar `aria-busy` e reabilitar o botão em ambos os resultados.
- Preservar as notificações, o bloqueio contra envios duplicados e a retenção
  dos campos em caso de falha.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
