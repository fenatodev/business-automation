# WP-441 — Feedback de falha na atualização do dashboard

## Objetivo

Informar o operador quando a consulta do dashboard falhar e permitir uma nova
tentativa pelo botão Atualizar já existente.

## Escopo

- Exibir estado acessível durante atualização e uma mensagem genérica em falha
  de rede, resposta HTTP não bem-sucedida ou leitura do corpo.
- Limpar a mensagem após atualização bem-sucedida.
- Preservar o tratamento de 403 e ignorar resultados obsoletos de polling ou
  sessão.
- Testar o handler real com respostas sintéticas controladas.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
