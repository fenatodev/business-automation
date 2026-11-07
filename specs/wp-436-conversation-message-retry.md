# WP-436 — Retry do carregamento de mensagens da conversa

## Objetivo

Permitir que o operador tente novamente o carregamento da página atual de
mensagens após falha, sem precisar trocar de conversa ou alterar a paginação.

## Escopo

- Anunciar carregamento e falha com estado acessível e mensagem genérica.
- Exibir o retry somente após falha e desabilitá-lo enquanto carrega.
- Repetir apenas as consultas GET da conversa selecionada e página atual.
- Ignorar respostas obsoletas segundo os guards existentes de seleção e sessão.
- Testar os handlers reais com DOM e API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
