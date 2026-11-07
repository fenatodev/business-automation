# WP-438 — Retry de customers relacionados à oportunidade

## Objetivo

Permitir recuperar a lista de customers ligados à oportunidade selecionada após
uma falha de leitura, sem precisar trocar de oportunidade.

## Escopo

- Exibir status acessível de carregamento e falha, com mensagem genérica.
- Mostrar retry somente após falha e desabilitá-lo durante a consulta.
- Repetir somente o GET de customers da oportunidade selecionada.
- Ignorar respostas de seleção ou sessão anteriores.
- Cobrir falha, retry bem-sucedido e respostas obsoletas com DOM/API sintéticos.
- Sem mudanças em API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
