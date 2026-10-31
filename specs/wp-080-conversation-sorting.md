# WP-080 — Ordenação de conversas no operador

Base: `origin/wp/079-conversation-pagination`.
Branch: `wp/080-conversation-sorting`.

## Motivação

As conversas eram ordenadas apenas por ID ascendente. O operador precisa ver
as conversas mais ativas primeiro — aquelas com a última mensagem mais recente.

## Entrega

### Backend (conversations.py)

- `list_company_conversations` aceita `sort` (default "last_message").
- Opções: `last_message` (subquery max(Message.created_at)), `created_at`
  (desc), `id` (asc).
- Valor inválido decai para ordenação por ID.
- Ordenação combina com filtros (channel, status, q) e paginação (limit/offset).

### UI (index.html)

- Dropdown "Ordenar" com opções: Última mensagem, Data de criação, ID.

### JavaScript (app.js)

- `convFilterSort` estado (default "last_message").
- `buildConversationUrl()` inclui `sort` nos query params.
- `clearConversationFilters()` reseta para "last_message".
- Listener de `change` no dropdown reseta offset e recarrega.

### Testes

- 9 testes backend: default sort, id asc, created_at desc, sem mensagens,
  misto com/sem mensagens, paginação + ordenação, filtro + ordenação,
  valor inválido, count endpoint inalterado.

## Validação

- **1220 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-080 depende de WP-079 (paginação, PR #163).
