# WP-416 — Busca de conversas sem respostas fora de ordem

Branch: `wp/416-conversation-refresh-order`, base `main`.

## Entrega

Somente a atualização mais recente da lista de conversas pode aplicar lista,
contagem, badge, paginação, seleção, erro e fim de carregamento. Respostas
e falhas antigas são ignoradas e não anunciam sucesso. O retry mantém filtros
e página e repete apenas leituras. Usa os endpoints existentes, sem alterar
API, schema, migrations, autenticação ou serviços externos.

## Validação

Handlers reais em DOM sintético: buscas sobrepostas, sucesso/falha da lista
e contagem em ambas as ordens, seleção preservada após falha, badge,
carregamento e recuperação pelo retry. Manter teste de resultado vazio.
Executar pytest, compileall, diff-check, preflight e sintaxe JavaScript.
Entregar um único PR aberto ao supervisor, sem merge ou próxima WP.
