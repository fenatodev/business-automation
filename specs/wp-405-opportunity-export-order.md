# WP-405 — Ordenação no CSV de oportunidades

Branch: `wp/405-opportunity-export-order`, base `main`.

Completar o fluxo Exportar CSV da lista de oportunidades: transmitir ID, Data,
Status ou Prioridade e ordenar todos os resultados filtrados antes de exportar.
Preservar ID crescente quando sort for omitido; sort inválido retorna 422.
Data usa data e ID decrescentes, status usa status e ID crescentes e prioridade
usa score decrescente com ID crescente no empate, conforme contratos existentes.
Filtros existentes permanecem aplicados. A lista por prioridade usa endpoint
próprio; este WP não muda seu comportamento de filtros/paginação.

Cobrir API e listener real com fixtures sintéticas, empates, filtros, páginas,
arquivo vazio e isolamento existente. Sem schema, migrations, autorização ou
serviços externos. Validar pytest, compileall, diff-check, preflight e JS.
Entregar um único PR aberto ao supervisor, sem merge ou próximo WP.
