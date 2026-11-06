# WP-402 — CSV de conversas na ordem selecionada

Branch: `wp/402-conversation-export-order`, base `main`.

O botão Exportar CSV envia a ordenação selecionada (`id`, `created_at` ou
`last_message`), além dos filtros existentes. A API exporta todos os resultados
filtrados na mesma ordem da lista, sem paginação: ID crescente ou data/última
mensagem decrescente, com ID crescente no desempate. Sem `sort`, mantém ID
crescente para consumidores existentes; sort desconhecido retorna 422.

Testes de API e do listener real com DOM sintético cobrem filtros combinados,
ordens, empates, conversas sem mensagens, páginas, arquivo vazio e isolamento
existente. Sem schema, migrations, alteração de autorização ou ação externa.
Executar pytest, compileall, diff-check, preflight e sintaxe JavaScript.
Um único PR permanece aberto para CI e revisão pelo supervisor.
