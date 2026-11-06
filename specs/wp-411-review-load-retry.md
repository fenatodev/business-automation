# WP-411 — Recuperação da fila de revisão

Branch: `wp/411-review-load-retry`, base `main`.

A fila deve preservar resultados, resumo, atrasos, paginação e seleção quando
qualquer consulta de lista, resumo, atrasos ou contagem falhar. Exibir aviso
genérico e Tentar novamente, com carregamento anunciado por status e aria-busy.
Validar os contadores antes de substituir o snapshot. Respostas antigas não
podem substituir o estado de uma consulta mais recente; desconectar limpa feedback.

Retry repete apenas GETs existentes com filtros, ordenação e página atuais.
Não registra decisões, não reprocessa eventos nem envia mensagens. Após sucesso,
limpar seleção e manter o estado vazio normal. Sem API nova, schema, migrations,
mudanças de autorização, credenciais ou serviços reais.

Teste executa os handlers entregues com DOM e APIs sintéticos: falha de rede,
null e resposta inválida em cada uma das quatro consultas, preservação dos
dados e recuperação vazia com os mesmos filtros e página. Executar preflight
e sintaxe JavaScript; deixar um único PR aberto para o supervisor.
