# WP-430 — Evitar retries simultâneos no detalhe de customer

## Objetivo

Impedir que cliques repetidos no botão de retry de conversas do customer aberto
iniciem consultas GET concorrentes, informando estado de carregamento e
restaurando o controle ao concluir a tentativa.

## Escopo

- Desabilitar o botão enquanto a consulta de conversas estiver pendente.
- Anunciar o carregamento pelo elemento de status acessível existente.
- Reabilitar o botão em sucesso, lista vazia ou falha da seleção ainda aberta.
- Testar o handler real com DOM e respostas sintéticas, incluindo cliques
  repetidos e falha seguida de retry.
- Sem mudanças em API, schema, autorização, migrations, integrações ou serviços
  externos.

## Validação

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check` e `scripts/preflight.sh`.
