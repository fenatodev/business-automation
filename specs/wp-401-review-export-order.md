# WP-401 — CSV da fila na ordem selecionada

Branch: `wp/401-review-export-order`, base `main`.

## Entrega

O botão Exportar CSV da fila envia `sort=id|created_at|status`, junto com
status, busca e datas. A API exporta todos os resultados filtrados; data
decrescente, ID/status crescentes, ID crescente no desempate. Sem sort,
preserva ID crescente. Sort inválido retorna 422.

## Limites e validação

Sem schema, migrations, autorização, integrações ou serviços reais. Fixtures
sintéticas em SQLite isolado. Testes cobrem ordens, desempates, filtros,
paginação, arquivo vazio, isolamento existente e listener real do botão
com DOM sintético. Executar preflight e sintaxe JavaScript. Um único PR
permanece aberto para CI e revisão do supervisor.
