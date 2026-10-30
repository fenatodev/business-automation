# WP-064 — visibilidade das tarefas internas

Base: WP-063 integrada pelo PR #146 em `f5e869e`.
Branch: `wp/064-internal-task-visibility`.

## Entrega

- GET `/internal-tasks/`: lista paginada por criação/id decrescentes, filtro
  opcional queued/running/succeeded/failed; limit 1–100, offset não negativo.
- GET `/internal-tasks/summary`: contagens por estado, queued cuja disponibilidade
  venceu há mais de 24h e running com lease expirado. Snapshot SQL único.
- Ambos exigem operator e filtram Company autenticada. Não retornam payload,
  mensagem, claim token ou exceção. Admin não tem acesso implícito.
- Leitura não recupera/reexecuta tarefas nem muda estado. Retenção e retry
  manual continuam pendentes. Nenhuma alteração de schema ou workflow CI.

## Aceite

Testes de paginação determinística, filtro, privacidade, isolamento, autenticação,
limites, atraso e resumo vazio. Executar `uv run pytest`, compileall e diff-check;
CI existente deve passar. Usar somente fixtures sintéticas/SQLite isolado.

## Próximo passo

Integrar essas leituras ao painel do operador, com estados vazios e falhas de
consulta explícitos. Não ativar worker, workflow ou integração comercial real.
