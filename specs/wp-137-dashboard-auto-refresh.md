# WP-137 — Auto-refresh do dashboard e polling de notificações

**Data:** 31/10/2026
**Status:** Concluída

## Problema

O dashboard só atualizava manualmente (botão "Atualizar"). As notificações (WP-107) não tinham polling real — o badge pendente só era atualizado em `refreshList()`.

## Solução

`startDashboardRefresh()` inicia polling a cada 60s via `setInterval`. `startNotificationRefresh()` inicia polling a cada 30s para atualizar o badge pendente silenciosamente. Ambos são parados no `disconnect()`.

## Changes

- `app/operator_ui/app.js`: `dashboardIntervalId`, `DASHBOARD_REFRESH_MS` (60s); `startDashboardRefresh()`, `stopDashboardRefresh()`; `notificationIntervalId`, `NOTIFICATION_REFRESH_MS` (30s); `updateNotifications()`, `startNotificationRefresh()`, `stopNotificationRefresh()`; connect inicia ambos, disconnect para ambos
- `tests/test_wp137_dashboard_auto_refresh.py`: 15 testes de contrato UI

## Verification

- `uv run pytest`: **1938 passed**, 3 warnings
- `compileall` ✓
- `git diff --check` ✓
