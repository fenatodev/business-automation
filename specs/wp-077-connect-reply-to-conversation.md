# WP-077 — Conectar resposta manual à conversa selecionada

Base: `origin/main`.
Branch: `wp/077-connect-reply-to-conversation`.

## Motivação

WP-075 adicionou o histórico de conversas e WP-076 adicionou o formulário de
resposta manual, mas ambos vivem em seções separadas e o operador precisa
digitar manualmente o ID da conversa para responder. Além disso, como ambas
as WPs modificam a mesma seção "06 / COMUNICAÇÃO", elas conflitam ao serem
mescladas. Esta WP unifica as duas entregas e conecta o formulário de resposta
à conversa selecionada.

## Entrega

### UI (index.html)

- Seção "06 / COMUNICAÇÃO" unificada com:
  - Lista de conversas (`#conv-list`) e botão atualizar (`#conv-refresh`).
  - Visualizador de mensagens (`#conv-detail`, `#conv-messages`).
  - Formulário de resposta manual (`#human-reply-form`) integrado abaixo do
    detalhe da conversa, visível apenas quando uma conversa está selecionada.
  - O campo ID da conversa (`#reply-conv-id`) torna-se `readonly` e é
    preenchido automaticamente.
  - Botão "Responder" aparece no cabeçalho do detalhe da conversa.

### JavaScript (app.js)

- `conversationApi()` com allowlist estrita (padrão WP-075).
- `replyApi()` com allowlist restrita a `POST /conversations/{id}/messages`.
- `showConversationList()`, `selectConversation()`, `refreshConversations()`
  (padrão WP-075).
- Quando `selectConversation(id)` é chamado:
  - Preenche `#reply-conv-id` com o ID da conversa (readonly).
  - Torna o formulário de resposta visível (`#human-reply-form`).
  - Mostra o botão "Responder" no cabeçalho do detalhe.
- `channelLabels` e `senderLabels` em português.
- `disconnect()` limpa `conversations`, `selectedConvId` e esconde o formulário.
- Integração com o fluxo de conexão via `MutationObserver`.

### CSS (styles.css)

- Estilos de WP-075: `.conversation-list`, `.conversation-item`, `.conv-detail`,
  `.conv-messages`, `.message-bubble` com variantes por remetente.
- O formulário de resposta (`#human-reply-form`) fica oculto por padrão e
  visível quando `.conv-detail` está ativo.

## Design

- Sem mudanças no backend, modelo ou migração.
- Tenant isolation preservada: as conversas são carregadas por company_id.
- Allowlist estrita segue o padrão `reviewApi()`/`taskApi()`.
- O campo ID da conversa torna-se `readonly` para evitar confusão.
- O formulário só aparece quando há uma conversa selecionada.

## Aceite

- Testes de contrato UI validam elementos unificados, conexão automática do ID,
  visibilidade condicional do formulário e funções JS.
- `uv run pytest`: todos os testes passam.
- compileall ✓, git diff --check ✓.

## Próximo passo

Avaliar se é necessário um endpoint de busca de conversas por keywords ou
filtro por canal/status.
