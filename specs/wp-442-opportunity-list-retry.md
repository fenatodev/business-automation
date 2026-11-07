# WP-442 — Feedback e retry da lista de oportunidades

## Objetivo

Informar o operador quando a listagem principal de oportunidades falhar e
permitir nova tentativa sem perder o acesso à ação existente de atualização.

## Escopo

- Anunciar carregamento e falha genérica da consulta de oportunidades.
- Expor `aria-busy` enquanto a listagem está atualizando.
- Mostrar botão de nova tentativa somente após falha; ocultá-lo após sucesso.
- Reutilizar o carregamento atual e não apresentar detalhes internos do erro.
- Testar falha seguida de sucesso pelo handler real de retry com dados sintéticos.
- Sem mudanças na API, autorização, tenant, schema, migrations, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
