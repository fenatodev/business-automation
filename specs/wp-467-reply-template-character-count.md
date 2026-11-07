# WP-467 — Mostrar contagem dos campos de templates de resposta

## Objetivo

Deixar visível quanto do limite de caracteres resta ao criar um template.

## Escopo

- Mostrar a contagem atual e o limite para nome (100) e conteúdo (4000).
- Atualizar as contagens ao digitar, sem enviar requisições nem anunciar cada
  tecla em regiões live.
- Exercitar os listeners reais com DOM sintético.
- Sem mudanças na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
