# WP-066 — painel de tarefas internas

Base: WP-065 em `b14f79a` (branch `wp/065-review-pagination-route`, pendente de merge).
Branch: `wp/066-internal-task-panel`.

## Motivação

WP-064 entregou os endpoints `/internal-tasks/` e `/internal-tasks/summary`, mas
o painel do operador não os expõe. O operador não consegue ver o estado das
tarefas internas (queued, running, succeeded, failed) nem o resumo de atrasos.

## Entrega

- Painel "Tarefas internas" no `/operator` com:
  - Lista paginada de tarefas (limit 50, offset 0), ordenação por criação decrescente.
  - Filtro por status: todas, queued, running, succeeded, failed.
  - Resumo: contagens por estado + tarefas queued com atraso > 24h + running com lease expirado.
  - Botão atualizar e tratamento explícito de estados vazios e falhas.
- `taskApi()` com allowlist estrita, seguindo o padrão de `reviewApi()`.
- Nenhuma alteração de backend, schema, ou workflow CI.
- Worker não é ativado; apenas leitura de estado.

## Aceite

- Teste runtime (Node.js + DOM sintético) valida:
  - Conexão carrega tarefas e resumo.
  - Filtro por status funciona.
  - Rotas inválidas rejeitadas antes do fetch.
  - Opções de fetch preservadas (Bearer, credentials, redirect, cache, referrerPolicy).
- `uv run pytest`, compileall, node --check, git diff --check: PASS.
- Segunda revisão antes de integração.

## Próximo passo

Após integração, avaliar retenção e retry manual das tarefas internas.
