# WP-081 — Fechar conversas no operador

Base: `origin/wp/080-conversation-sorting`.
Branch: `wp/081-close-conversation`.

## Motivação

O modelo Conversation possui um campo `status` (open/closed) e o operador já
pode filtrar por status, mas não havia endpoint para atualizá-lo. O operador
precisa fechar conversas resolvidas e reabri-las quando necessário.

## Entrega

### Backend (schemas.py, conversations.py)

- `ConversationUpdate` schema com `status: Literal["open", "closed"]`.
- `PATCH /conversations/{conversation_id}` atualiza o status com tenant isolation.

### UI (index.html, app.js, styles.css)

- Botão "Fechar" no header do detalhe da conversa.
- Toggle entre open/closed; após fechar, a lista é recarregada.
- `.conv-detail-actions` wrapper flex para botões de ação.

### Testes

- 9 testes backend (fechar, reabrir, auth, 404, status inválido, tenant
  isolation, reflexão na lista, filtro por status, count com filtro).

## Validação

- **1229 testes passaram**, 2 warnings preexistentes
- compileall ✓, git diff --check ✓

## Notas

WP-081 depende de WP-080 (ordenação, PR #164).
