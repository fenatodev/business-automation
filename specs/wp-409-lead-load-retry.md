# WP-409 — Recuperação da listagem de leads

Branch: `wp/409-lead-load-retry`, base `main`.

Falhas na lista ou contagem de leads devem preservar resultados, contagem,
badge, detalhe e seleção anteriores. Mostrar aviso genérico de dados
possivelmente desatualizados, carregamento acessível e Tentar novamente.
O retry repete somente GETs com filtros, ordenação e página atuais.
Resultado vazio bem-sucedido continua vazio; sucesso só é anunciado após
ambas as consultas concluírem.

Cobrir handlers reais em DOM sintético: falhas de rede e respostas null,
lista e contagem, recuperação vazia, filtros, página e notificação.
Executar preflight e sintaxe JavaScript. Sem API, schema, migrations,
autorização, serviços reais ou ações externas. Um PR aberto ao supervisor.
