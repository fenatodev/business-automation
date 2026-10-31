# WP-107 — Notificações visuais no operador

**Status:** Concluída
**Branch:** `wp/107-opportunity-notifications`
**Depende de:** WP-106 (PR #189)

## Problema

O operador não tinha indicação visual de que havia itens pendentes sem precisar navegar até cada seção. O badge de pendentes (WP-091) mostrava apenas oportunidades, sem agregar leads novos ou conversas abertas.

## Solução

Sino de notificações na barra superior que agrega contagens de oportunidades pendentes, leads novos e conversas abertas. Atualização automática a cada 30 segundos via polling. Tooltip detalhado ao passar o mouse.

## Changes

### UI

- **`index.html`**: Botão de sino 🔔 na topbar com contador vermelho; wrapper `.topbar-right` para layout flex.
- **`app.js`**: `updateNotificationBell()` consulta `/opportunities/count`, `/leads/count` e `/conversations/count`; `startNotificationPolling()` inicia polling a cada 30s; `stopNotificationPolling()` para no disconnect.
- **`styles.css`**: `.topbar-right`, `.notification-bell`, `.notification-count` (badge vermelho com border-radius).

## Segurança

- O polling usa os mesmos endpoints count existentes, já protegidos por autenticação Bearer.
- Nenhum dado novo é exposto; apenas contagens agregadas.
- Erros de polling são silenciosos — notificações são não-críticas.

## Verificação

- 1572 testes passaram, 2 warnings preexistentes.
- `compileall` ✓, `git diff --check` ✓.
