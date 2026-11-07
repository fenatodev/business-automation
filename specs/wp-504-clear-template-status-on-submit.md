# WP-504 — Limpar aviso de template após envio da resposta

## Objetivo

Remover a confirmação de inserção de template depois que a resposta contendo
esse template for enviada com sucesso.

## Escopo

- Limpar o aviso após a resposta ser aceita pela API e o formulário ser resetado.
- Preservar o aviso e o rascunho se o envio falhar.
- Cobrir o listener real de envio com DOM e API sintéticos.
- Sem alterações de API, autorização, tenant, persistência, schema, migrations,
  integrações ou serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh` quando presente.
