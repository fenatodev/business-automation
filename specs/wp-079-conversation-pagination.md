# WP-079 — Paginação de conversas no operador

Base: `origin/wp/078-conversation-search-filter`.
Branch: `wp/079-conversation-pagination`.

## Motivação

O endpoint `GET /companies/{company_id}/conversations` retornava todas as
conversas sem paginação. Com o crescimento das conversas, a lista torna-se
lenta e consome memória desnecessária. A fila de revisão já usa o padrão
`limit/offset` — as conversas devem seguir o mesmo modelo.

## Entrega

### Backend (conversations.py)

- `list_company_conversations` aceita `limit` (default 50, max 100) e
  `offset` (default 0) via `.offset().limit()` no SQLAlchemy.
- Novo endpoint `GET /companies/{company_id}/conversations/count` retorna
  `{"total": N}` aplicando os mesmos filtros (channel, status, q).
- Filtros e paginação são combináveis.

### UI (index.html)

- Controles de paginação após a lista: botões Anterior/Próxima e
  indicador "Página X de Y (N total)".
- Ocultos quando o total cabe em uma página.

### JavaScript (app.js)

- `convOffset`, `convPageSize` (50), `convTotal` para estado de paginação.
- `buildConversationUrl()` inclui `limit` e `offset` nos query params.
- `buildConversationCountUrl()` para fetch paralelo da contagem.
- `refreshConversations()` faz `Promise.all` das conversas + count.
- `updateConversationPagination()` controla visibilidade e estado dos botões.
- Filtros resetam `convOffset` para 0.
- `conversationApi()` allowlist aceita `/conversations/count`.

### CSS (styles.css)

- `.conv-pagination` com layout flex centralizado.

## Aceite

- 14 testes backend (limit, offset, paginação, filtros combinados, count).
- `uv run pytest`: **1211 testes passaram**.
- compileall ✓, git diff --check ✓.

## Notas

- WP-079 depende de WP-078 (busca e filtro de conversas).
- A paginação usa offset-based, não keyset, para simplicidade e
  compatibilidade com os filtros existentes.
