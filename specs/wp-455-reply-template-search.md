# WP-455 — Buscar templates de resposta

## Objetivo

Permitir que o operador encontre rapidamente um template pelo nome ou pelo
conteúdo, diretamente na interface de gerenciamento.

## Escopo

- Adicionar um campo de busca local à lista de templates.
- Filtrar a lista sem nova chamada à API e permitir limpar a busca para voltar
  a exibir todos os templates.
- Anunciar quando nenhum template corresponder à busca.
- Continuar exibindo o estado vazio normal quando a lista não possui templates.
- Exercitar o handler real com DOM e respostas sintéticas.
- Sem mudanças na API, autorização, tenant, persistência, integrações ou
  serviços externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
