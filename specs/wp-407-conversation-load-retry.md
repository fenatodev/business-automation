# WP-407 — Recuperação de falhas na listagem de conversas

Branch: `wp/407-conversation-load-retry`, base `main`.

Problema: falhas na consulta de conversas ou na contagem apagavam a lista,
mostravam um estado vazio e permitiam a notificação de atualização concluída.

Entregar o fluxo de falha e recuperação na UI existente: indicador de carga,
mensagem genérica acessível e botão Tentar novamente. Preservar resultados
anteriores, seleção, filtros, ordenação e página após falha; informar que os
dados podem estar desatualizados. A nova tentativa repete as consultas de
leitura. Uma resposta vazia bem-sucedida continua sendo um resultado vazio,
sem erro. Não mostrar detalhes internos nem notificação de sucesso na falha.

Validar os handlers reais em DOM sintético com falhas na lista e contagem,
recuperação para resultado vazio, filtros/página preservados e notificação.
Executar pytest, compileall, diff-check, preflight e sintaxe JS.
Sem alterações de API, schema, migrations, autorização ou serviços externos.
Entregar um único PR aberto ao supervisor.
