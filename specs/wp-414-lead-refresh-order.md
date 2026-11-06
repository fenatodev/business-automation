# WP-414 — Busca de leads sem respostas fora de ordem

Branch: `wp/414-lead-refresh-order`, base `main`.

## Problema e entrega

Buscas sucessivas iniciam GETs concorrentes para lista e contagem. Uma resposta
antiga pode substituir a busca atual, alterar paginação/badge ou esconder o
carregamento da consulta mais recente. Somente a última atualização iniciada
pode aplicar dados, erro ou conclusão de carregamento e anunciar sucesso.

Preservar filtros, ordenação, paginação e o retry existente. Respostas antigas
são ignoradas; nenhuma escrita ou consulta adicional é introduzida. Reutilizar
os endpoints existentes, sem mudanças de API, schema, auth ou serviços.

## Validação

Executar handlers reais de busca/atualização/retry em DOM sintético, com lista
e contagem controladas: respostas antigas antes/depois da atual, sucesso e
falha de cada geração, preservação de estado/busy e recuperação por retry.
Manter os testes de falha isolada existentes. Executar pytest, compileall,
diff-check, preflight e sintaxe JavaScript. Um PR aberto ao supervisor;
sem merge, dados reais, migrations, envio ou próxima WP.
