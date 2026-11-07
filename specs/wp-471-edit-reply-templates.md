# WP-471 — Editar templates de resposta

## Objetivo

Permitir que operadores corrijam nome e conteúdo de templates existentes sem
excluir e recriar o item.

## Escopo

- Adicionar `PUT /companies/{company_id}/reply-templates/{template_id}` usando
  o contrato de campos e limites existente.
- Preservar a verificação de Company do operador e retornar 404 para template
  ausente dentro da Company autorizada.
- Permitir iniciar, cancelar e salvar a edição na UI do operador; atualizar a
  lista e o seletor após sucesso.
- Cobrir validação, autenticação, isolamento e fluxo da interface com fixtures
  e dados sintéticos.
- Sem persistência nova, migration, alteração de auth, integração ou serviço
  externo.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
