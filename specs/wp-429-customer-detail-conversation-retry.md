# WP-429 — Retry de conversas no detalhe de customer

## Objetivo

Permitir que o operador recupere a listagem de conversas do customer selecionado
quando a consulta falhar, sem expor detalhes internos nem aceitar respostas de
uma seleção ou sessão anterior.

## Escopo

- Adicionar estado acessível de falha e botão de retry ao detalhe de customer.
- Repetir somente a consulta GET existente para o customer aberto.
- Manter a mensagem de lista vazia em respostas válidas sem conversas.
- Testar o handler real com API e DOM sintéticos, incluindo falha, retry e
  resposta obsoleta após trocar a seleção.
- Sem mudanças em API, schema, autorização, migrations, integrações ou serviços
  externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
