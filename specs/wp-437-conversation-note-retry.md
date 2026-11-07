# WP-437 — Retry do carregamento da nota interna

## Objetivo

Permitir que o operador recupere a nota interna da conversa selecionada após
falha de leitura, sem precisar trocar de conversa.

## Escopo

- Exibir um botão de nova tentativa somente após falha; mantê-lo desabilitado
  durante o carregamento.
- Repetir somente o GET da nota da conversa ainda selecionada.
- Preservar os guards atuais de seleção e sessão para respostas obsoletas.
- Testar falha, retry bem-sucedido e estado do editor usando DOM/API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
