# WP-465 — Devolver foco após salvar template de resposta

## Objetivo

Manter a criação de templates de resposta fluida para quem usa teclado.

## Escopo

- Após a API confirmar o salvamento, limpar os campos e focar o campo de nome.
- Em caso de falha, preservar os valores e não mover o foco.
- Exercitar o handler real com API e DOM sintéticos.
- Sem mudanças na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
