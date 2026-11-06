# WP-418 — Histórico de mensagens com paginação consistente

Branch: `wp/418-message-page-order`, base `main`.

## Problema e entrega

Cliques sucessivos em Próxima/Anterior iniciam consultas concorrentes da mesma
conversa. O guard existente verificava apenas o ID da conversa: uma página
antiga podia substituir as mensagens depois de carregar a página atual,
com indicador de página incorreto. Uma falha antiga também podia gerar aviso.

Somente a consulta mais recente de mensagens pode atualizar o histórico,
contagem, paginação ou aviso de falha. Preservar o guard de conversa e
invalidar resultados de sessões encerradas. Usar os endpoints GET existentes;
nenhuma alteração de API, schema, migrations, autenticação ou envio de mensagens.

## Validação

Teste dos handlers reais de paginação com DOM sintético e promises controladas:
16 combinações de ordem de conclusão, sucesso/falha e endpoint com falha
(lista ou contagem); recuperação pela navegação e descarte após fim da sessão.
Executar `bash scripts/preflight.sh` e `node --check app/operator_ui/app.js`.
Entregar um único PR aberto ao supervisor, sem merge nem próxima WP.

## Evidência local

`bash scripts/preflight.sh`: PASS — 3283 testes passaram, 2 warnings;
compileall e diff-check passaram. Sintaxe JavaScript: PASS.
Nenhuma migration, dado real, serviço privado ou mensagem externa foi usado.
