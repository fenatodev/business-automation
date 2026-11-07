# WP-446 — Evitar gravações duplicadas da configuração do agente

## Objetivo

Impedir que cliques repetidos em Salvar enviem gravações concorrentes da mesma
configuração do agente.

## Escopo

- Ignorar submissões enquanto uma gravação estiver em andamento.
- Desabilitar o botão durante a requisição e reabilitá-lo em sucesso ou falha.
- Preservar o payload e as mensagens de resultado existentes.
- Exercitar o handler real com API e DOM sintéticos, incluindo sucesso e falha.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh` quando disponível.
