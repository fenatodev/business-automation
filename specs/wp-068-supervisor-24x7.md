# WP-068 — Supervisor 24×7 para fila de tarefas internas

Base: `origin/main` (após merge WP-063/064/065/066/067).
Branch: `wp/068-supervisor-24x7`.

## Motivação

`run_once()` executa uma única iteração da fila. Em produção, é necessário um
processo contínuo que mantenha a fila ativa 24×7, com tratamento de sinais
graceful, controle de polling e métricas básicas de saúde.

## Entrega

### Módulo supervisor

- `app/services/supervisor.py` — loop contínuo sobre `tasks.run_once()`.
- Polling interval configurável (default: 5 segundos).
- Tratamento de `SIGTERM` e `SIGINT` para shutdown graceful:
  completar a iteração em curso e encerrar limpa.
- Tracking de estatísticas: ciclos executados, tarefas processadas, erros.
- `SupervisorStats` dataclass: `cycles`, `tasks_processed`, `errors`, `running`.
- Função `run(session_factory, service_context, *, interval=5)` — bloca até
  receber sinal de parada.
- Função `run_loop(session_factory, service_context, *, interval=5, max_cycles=None)`
  — retorna `SupervisorStats`; útil para testes (max_cycles limita iterações).

### Script CLI

- `scripts/run_supervisor.py` — entrada standalone para execução direta:
  lê `DATABASE_URL` e `BA_INTAKE_SERVICE_CONTEXT` do ambiente.
- Imprime status no início e a cada ciclo (log básico via print).
- Não depende de FastAPI ou Uvicorn; processo independente.

## Design

- O supervisor não altera o comportamento de `run_once()`.
- Cada ciclo é independente: `run_once()` abre e fecha sua própria sessão.
- Erros em `run_once()` são capturados e registrados nas estatísticas,
  sem derrubar o processo.
- Shutdown graceful espera no máximo `interval` segundos após o sinal
  para completar a iteração em curso.

## Aceite

- Testes unitários validam:
  - `run_loop` executa N ciclos quando `max_cycles=N`.
  - Estatísticas contam ciclos, tarefas processadas e erros.
  - Erros em `run_once()` não derrubam o loop.
  - `SupervisorStats` expõe contadores corretos.
- `uv run pytest`, compileall, git diff --check: PASS.
- Script CLI compila sem erro: `python scripts/run_supervisor.py --help`
  (ou equivalente de verificação).

## Próximo passo

Após integração, avaliar integrações externas (n8n workflow activation, etc).
