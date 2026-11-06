# WP-406 — CSV de briefs na ordem selecionada

Branch: `wp/406-brief-export-order`, base `main`.

Completar o fluxo Exportar CSV dos briefs: transmitir ID, Data, Status ou
Título e ordenar todos os resultados filtrados, sem limite de página.
Sem sort, manter ID crescente; sort inválido retorna 422. Data e desempate
por ID são decrescentes; status/título e ID de desempate são crescentes,
conforme a listagem existente. Preservar filtros e campos detalhados.

Validar API e listener real do botão com dados sintéticos: empates, filtros,
paginação, arquivo vazio e isolamento existente. Executar pytest, compileall,
diff-check, preflight e sintaxe JS. Sem schema, migrations, autorização,
serviços externos ou dados reais. Entregar um único PR aberto ao supervisor.
