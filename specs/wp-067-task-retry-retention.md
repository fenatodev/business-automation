# WP-067 — retry manual e retenção de tarefas internas

Base: `origin/main` (após merge WP-063/064/065/066).
Branch: `wp/067-task-retry-retention`.

## Motivação

O operador não pode reprocessar manualmente uma tarefa falhada e as tarefas
concluídas ou falhadas acumulam indefinidamente. O painel de tarefas (WP-066)
mostra o estado, mas não oferece ação corretiva nem controle de retenção.

## Entrega

### Retry manual

- `POST /internal-tasks/{task_id}/retry` — re-enfileira uma tarefa `failed`
  para `queued`, resetando o lease e mantendo a contagem de attempts.
- A tarefa deve estar em estado `failed` e pertencer ao tenant do operador.
- Se a tarefa já atingiu `MAX_ATTEMPTS`, o retry manual ainda é permitido
  (override explícito do operador), mas o attempt counter é preservado para
  que o worker respeite o limite na próxima execução.
- Retorna `404` se a tarefa não existe, `409` se não está em estado `failed`.

### Retenção

- `POST /internal-tasks/retention` — remove tarefas `succeeded` e `failed`
  mais antigas que um número configurável de dias (default: 30).
- Apenas tarefas terminadas (`succeeded`/`failed`) são elegíveis.
- Tarefas `queued`/`running` nunca são removidas.
- Retorna contagem de tarefas removidas.
- Operador-only; isolado por tenant.

### Serviço

- `manual_retry(db, task_id, company_id)` em `app/services/internal_tasks.py`.
- `purge_old_tasks(db, company_id, older_than_days)` em `app/services/internal_tasks.py`.
- Nenhuma migration; usa apenas os campos existentes do modelo.

## Aceite

- Testes unitários validam:
  - Retry manual de tarefa falhada → status queued, lease limpo.
  - Retry rejeita tarefas não-falhadas (409).
  - Retry rejeita tarefas de outro tenant (404).
  - Retenção remove apenas tarefas terminadas antigas.
  - Retenção preserva queued/running independentemente da idade.
  - Retenção isolada por tenant.
- `uv run pytest`, compileall, git diff --check: PASS.
- Segunda revisão antes de integração.

## Próximo passo

Após integração, avaliar supervisor 24×7 e integrações externas.
