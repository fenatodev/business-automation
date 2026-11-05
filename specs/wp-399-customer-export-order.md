# WP-399 — Exportar clientes na ordem selecionada

## Problema e entrega

O operador podia ordenar clientes por ID, data ou nome, mas o CSV sempre
vinha por ID crescente. O botão agora envia a ordenação selecionada para
GET /customers/export.csv junto com busca e intervalo de datas.

O parâmetro sort aceita id (crescente, padrão anterior), created_at
(decrescente) e name (crescente). Empates usam ID crescente. Valor
desconhecido retorna 422. O CSV inclui todos os resultados filtrados,
independentemente da paginação da lista.

## Escopo e aceite

Branch: wp/399-customer-export-order, base main.
Sem alteração de autorização, schema ou migrations. Sem serviços externos,
dados reais ou PostgreSQL real. Fixtures usam SQLite isolado.

Testes verificam as três ordens, empates, filtros combinados, compatibilidade
sem sort, arquivo vazio, isolamento e exportação além da página visível.
Um teste Node executa o listener real do botão com DOM sintético e confirma
URL, nome do arquivo e codificação dos filtros para cada ordenação.

Validação obrigatória: scripts/preflight.sh (pytest, compileall e diff-check),
mais node --check app/operator_ui/app.js.
Um único PR fica aberto para CI e revisão pelo supervisor.

## Evidência local

27 testes direcionados passaram. Preflight: 3225 testes passaram, 2 warnings;
compileall e diff-check passaram (PREFLIGHT PASS). Sintaxe JavaScript validada.
Diff revisado sem segredos, dados reais, credenciais ou arquivos adjacentes.
