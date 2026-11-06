# WP-410 — Recuperação da listagem de tarefas internas

Branch: `wp/410-task-load-retry`, base `main`.

Falhas de rede ou respostas inválidas na lista/contagem devem preservar os
resultados, contagem, paginação e seleção anteriores. Mostrar aviso genérico
de dados possivelmente desatualizados e botão Tentar novamente. Anunciar
carregamento com status acessível e aria-busy. Retry repete somente GETs com
filtros, ordenação e página atuais; nunca reprocessa tarefas. Apenas após
sucesso atualizar resultados e limpar seleção, mantendo o estado vazio normal.

Validar handlers reais em DOM sintético: lista/contagem, rede, null, resposta
inválida, recuperação vazia, seleção, filtros e página. Executar preflight e
sintaxe JavaScript. Sem API, schema, migrations, autorização, serviços reais
ou ações externas. Deixar um único PR aberto para o supervisor.
