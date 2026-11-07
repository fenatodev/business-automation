# WP-460 — Reinsertir template de resposta sem alternar opções

## Objetivo

Permitir inserir o mesmo template de resposta mais de uma vez em sequência.

## Escopo

- Após inserir conteúdo válido de template no rascunho, retornar o seletor ao
  placeholder para que a mesma opção possa ser escolhida novamente.
- Manter a seleção do cursor e o restante do rascunho conforme WP-459.
- Cobrir o handler da UI com DOM sintético.
- Sem alterações na API, autorização, tenant, persistência ou integrações.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
