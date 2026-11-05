# WP-397 — Exportar tarefas na ordem selecionada

## Problema e entrega

O operador podia ordenar tarefas por data, ID, status ou tentativas, mas o CSV
sempre vinha por ID crescente. O botão agora envia a ordenação selecionada ao
GET `/internal-tasks/export.csv`, junto com status, busca e intervalo de datas.
O arquivo contém todos os resultados filtrados, independentemente da página.

O parâmetro opcional `sort` aceita `id`, `created_at`, `status`, `attempts`.
Quando informado, segue a lista: decrescente, com desempate por ID decrescente.
Sem `sort`, mantém o contrato anterior de ID crescente. Valor inválido retorna
422. Autenticação, tenant, campos exportados e filtros permanecem existentes.

## Escopo e aceite

Branch: `wp/397-task-export-order`, base `main`.
Sem migrations, worker, PostgreSQL real, dados reais ou ações externas.
Testes usam SQLite isolado e Node com listener real do botão e DOM sintético.
Cobrem as quatro ordens, desempate, filtros combinados, ausência de paginação,
tenant, arquivo vazio, compatibilidade e rejeição de ordenação desconhecida.

Executar `uv run pytest`, `.venv/bin/python -m compileall app tests`,
`git diff --check`, `scripts/preflight.sh` e `node --check app/operator_ui/app.js`.
Abrir um único PR; revisão, CI e merge ficam com o supervisor.

## Evidência local

- 53 testes direcionados passaram.
- `scripts/preflight.sh`: 3219 testes passaram, 2 warnings; compileall e
  diff-check passaram (`PREFLIGHT PASS`).
- Sintaxe JavaScript e teste Node do botão passaram.
- Diff revisado: somente API/UI de ordenação de exportação, testes e docs;
  sem segredos, dados reais, migrations ou mudanças de autorização.
