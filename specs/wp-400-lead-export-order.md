# WP-400 — Exportar leads na ordem selecionada

Branch: `wp/400-lead-export-order`, base `main`.

## Entrega

O operador seleciona ID, Data, Status ou Nome na lista de leads e exporta
CSV na mesma ordem, preservando status, fonte, busca e datas. A API
`GET /leads/export.csv` recebe `sort=id|created_at|status|name`.
Data é decrescente; ID, status e nome são crescentes, com ID crescente
no desempate. Sem sort, mantém ID crescente. Sort desconhecido retorna 422.
Todos os resultados filtrados são exportados, independentemente da página.

## Limites e aceite

Sem mudanças de schema, migrations, autorização ou integrações externas.
SQLite isolado e dados sintéticos nos testes; nenhum serviço real utilizado.
Testes verificam as quatro ordens, desempates, filtros combinados, paginação,
arquivo vazio, compatibilidade, isolamento existente e rejeição de sort inválido.
Teste Node executa o listener real do botão com DOM sintético e confirma
URL, encoding dos filtros e nome do arquivo.

Executar `scripts/preflight.sh` (pytest, compileall e diff-check) e
`node --check app/operator_ui/app.js`. Abrir um único PR e deixar revisão,
CI e merge com o supervisor.

## Evidência local

38 testes direcionados passaram. `scripts/preflight.sh`: 3232 testes
passaram, 2 warnings; compileall e diff-check passaram (PREFLIGHT PASS).
`node --check app/operator_ui/app.js` passou. Diff revisado sem segredos,
dados reais, credenciais, migrations ou arquivos fora do escopo.
