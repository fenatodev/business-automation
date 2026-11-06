# WP-408 — Recuperação da listagem de clientes

Branch: `wp/408-customer-load-retry`, base `main`.

Entregar na seção Clientes um fluxo completo de falha e recuperação: indicador
acessível de carregamento, aviso genérico de dados possivelmente desatualizados
e botão Tentar novamente. Falha na lista ou contagem deve preservar resultados,
contagem, detalhe e seleção anteriores. A tentativa repete somente GETs com
filtros, ordenação e página atuais. Resultado vazio bem-sucedido deve continuar
sendo mostrado como vazio. Não anunciar atualização concluída após falha.

Testar handlers reais em DOM sintético para erros de rede e retornos null da
API, falhas na lista e contagem, recuperação vazia, filtros e paginação.
Executar preflight (pytest, compileall e diff-check) e sintaxe JavaScript.
Sem alterações de API, autorização, schema, migrations ou serviços externos.
Um único PR aberto para o supervisor; sem merge nesta execução.
