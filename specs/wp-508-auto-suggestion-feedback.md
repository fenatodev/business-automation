# WP-508 — Feedback para falha de sugestão automática

## Objetivo

Ao abrir o formulário de resposta, informar ao operador quando a sugestão
automática não estiver disponível ou falhar, preservando a opção de escrever
manualmente.

## Escopo e limites

- Exibir feedback acessível para ausência de mensagem do cliente, agente
  indisponível e demais falhas de rede/servidor.
- Não substituir rascunho digitado nem exibir feedback atrasado para outra
  conversa ou formulário fechado.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos. Testes usam apenas respostas sintéticas.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
