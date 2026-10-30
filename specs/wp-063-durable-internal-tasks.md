# WP-063 — tarefas internas duráveis

## Objetivo

Persistir uma solicitação sintética de triagem, processá-la por worker do mesmo
monólito e registrar resultado na fila de revisão humana. Nenhum envio externo,
LLM, n8n real ou deploy faz parte desta WP.

Base verificada no GitHub: `415b6385b0580c59e0ccbd3eaad5b6d9aaa6f151`.
Branch: `wp/063-durable-internal-tasks`.

## Contrato

- `POST /internal-tasks/`: identidade operator existente; corpo igual a
  `ReviewQueueTrigger`; tenant exclusivamente autenticado. Retorna 202.
- `(company_id, event_id)` é a identidade persistente. Replay idêntico retorna
  a tarefa existente; payload divergente retorna 409.
- `GET /internal-tasks/{id}`: status, tentativas, código de falha genérico e
  ID do resultado; 404 cross-tenant. Admin não recebe acesso implícito.
- Worker explícito `uv run python -m app.worker`; `--once` processa no máximo
  uma tarefa. Não inicia automaticamente junto da API.
- Estados queued/running/succeeded/failed; três tentativas, lease de 60s,
  backoff de 2^attempts segundos; recuperação em lotes de até 100.
- Claim atômico, token novo por tentativa e fencing antes de qualquer escrita
  de resultado. Item de revisão e conclusão compartilham commit.
- Efeito interno deduplicado. Não promete execução computacional exatamente
  uma vez: uma tentativa interrompida pode repetir a triagem determinística.
- O handler só admite triagem local curta. Não adicionar rede/LLM sob o lock.
- Falha terminal exige intervenção; reprocessamento manual ainda não exposto.

## Validação e gates

`uv run pytest`, `.venv/bin/python -m compileall app tests`, `git diff --check`.
Segunda revisão de schema/concorrência antes de executar
`bash scripts/verify-alembic-postgres.sh`. Esse harness cria e remove somente
seu PostgreSQL descartável e inclui corridas de claim e restart/fencing.
CI obrigatório antes de integração. Nada autoriza migration em produção.

## Continuidade

Junie pode reproduzir tudo por este repositório sem plugins. Status final,
contagem efetiva e pendências ficam em `docs/operations/development-continuity.md`.
Próximo recorte: visibilidade operacional de tarefas falhas/atrasadas, mantendo
os gates humanos e sem ativar consumidores comerciais reais.
