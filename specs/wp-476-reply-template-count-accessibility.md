# WP-476 — Associar contadores aos campos de templates

## Objetivo

Permitir que tecnologia assistiva identifique o limite e a contagem atual de
caracteres ao focar os campos de nome e conteúdo do template.

## Escopo

- Associar cada campo ao contador correspondente usando `aria-describedby`.
- Manter as contagens visuais e sua atualização atuais, sem anúncio a cada tecla.
- Cobrir as associações na marcação da interface.
- Sem mudanças de API, autorização, tenant, persistência, schema, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
