# WP-413 — Ordem das oportunidades na tela

Branch: `wp/413-opportunity-render-order`, base `main`.

Corrigir o renderer que reordena por ID decrescente os resultados já ordenados
pela API. Preservar a sequência recebida para ID, Data, Status e Prioridade,
inclusive páginas filtradas e re-renderizações após seleção.

Cobrir API SQLite isolada → renderer JavaScript real com dados sintéticos,
lista vazia, seleção e abertura do detalhe. Reutilizar contratos existentes;
sem mudanças de API, schema, segurança ou paginação de prioridade.

Validar pytest, compileall, diff-check, preflight e sintaxe JavaScript.
Entregar um PR aberto ao supervisor, sem merge ou próxima WP.
