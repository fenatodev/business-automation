# WP-076 — Resposta manual do operador em conversas

Base: `origin/main`.
Branch: `wp/076-human-reply-ui`.

## Motivação

O operador não podia enviar mensagens humanas diretamente na UI. O endpoint
`POST /conversations/{id}/messages` já existia, mas não havia interface para
usá-lo. O operador precisava de um canal para responder manualmente após
revisar o contexto da conversa.

## Entrega

### UI (index.html)

- Seção "06 / COMUNICAÇÃO" com formulário de resposta manual.
- Campo ID da conversa (numérico, mínimo 1) e textarea de mensagem (max 4000).
- Botão "Enviar mensagem".

### JavaScript (app.js)

- `replyApi()` com allowlist estrita: apenas `POST /conversations/{id}/messages`.
- Handler de submit com validação de ID numérico e campos obrigatórios.
- `sender_type: "human"` fixo — o operador envia como humano, não como agente.
- Formulário resetado após envio bem-sucedido.

## Design

- Sem mudanças no backend, modelo ou migração.
- Tenant isolation preservada pelo endpoint existente.
- Allowlist restrita a uma única rota POST.
- Validação client-side de ID numérico antes do envio.

## Aceite

- 14 testes de contrato UI validam elementos, funções e comportamento.
- `uv run pytest`: **1142 passed**, compileall ✓, git diff --check ✓.

## Próximo passo

Após WP-075 (histórico de conversas) ser integrado, considerar conectar o
formulário de resposta à conversa selecionada, preenchendo automaticamente
o ID da conversa.
