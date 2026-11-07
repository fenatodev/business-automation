# WP-428 — Retry de conversas no detalhe de lead

## Objetivo
Quando a consulta de conversas do lead falhar, mostrar uma mensagem genérica e
um botão para tentar novamente, sem descartar o restante do detalhe ou exibir
detalhes internos. O retry repete somente a consulta de leitura do lead aberto.

## Escopo
- Atualizar `app/operator_ui/index.html` e `app/operator_ui/app.js`.
- Testar handlers reais com DOM e API sintéticos.
- Reutilizar o controle de versão atual para ignorar resposta de um lead que já
  não está selecionado ou de uma sessão encerrada.
- Sem mudanças em API, schema, autorização, integrações ou operações externas.
