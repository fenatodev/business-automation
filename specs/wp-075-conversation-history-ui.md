# WP-075 — Histórico de conversas no painel do operador

Base: `origin/main`.
Branch: `wp/075-conversation-history-ui`.

## Motivação

O operador não tinha acesso ao histórico de conversas na UI. A API já expunha
`GET /companies/{id}/conversations` e `GET /conversations/{id}/messages`, mas
nenhuma seção da UI conectava esses endpoints. O operador precisava de uma
visão das conversas para acompanhar o contexto das interações com clientes.

## Entrega

### UI (index.html)

- Seção "06 / COMUNICAÇÃO" com lista de conversas (`#conv-list`) e visualizador
  de mensagens (`#conv-detail`, `#conv-messages`).
- Botão "Atualizar" (`#conv-refresh`) para recarregar a lista.
- O detalhe das mensagens fica oculto até o operador selecionar uma conversa.

### JavaScript (app.js)

- `conversationApi()` com allowlist estrita:
  - `GET /companies/{id}/conversations`
  - `GET /conversations/`
  - `GET /conversations/{id}/`
  - `GET /conversations/{id}/messages`
- `showConversationList()`: renderiza a lista ordenada por ID decrescente.
- `selectConversation(id)`: carrega e exibe as mensagens da conversa selecionada.
- `refreshConversations()`: carrega as conversas da company derivada das
  oportunidades e atualiza a lista.
- `channelLabels` e `senderLabels` para exibição em português.
- Integração com o fluxo de conexão via `MutationObserver` para carregar
  conversas quando o workspace se torna visível.
- `disconnect()` limpa `conversations` e `selectedConvId`.

### CSS (styles.css)

- `.conversation-list`, `.conversation-item` (padrão `.opportunity-item`).
- `.conv-detail`, `.conv-messages` com scroll vertical limitado.
- `.message-bubble` com variantes por tipo de remetente
  (`.customer`, `.agent`, `.human`).
- `.message-sender` e `.message-content` para estrutura de cada mensagem.

## Design

- Sem mudanças no backend, modelo ou migração.
- Tenant isolation preservada: as conversas são carregadas por company_id
  derivado das oportunidades do operador.
- Allowlist estrita segue o padrão `reviewApi()`/`taskApi()`.
- Bolhas de mensagem distinguem visualmente cliente, agente e humano.

## Aceite

- 19 testes de contrato UI validam elementos, funções, allowlist e estilos.
- `uv run pytest`: **1147 passed**, compileall ✓, git diff --check ✓.

## Próximo passo

Avaliar se é necessário um endpoint de busca de conversas por keywords ou
filtro por canal/status, ou se a listagem completa é suficiente para o piloto.
