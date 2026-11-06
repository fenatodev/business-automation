# WP-415 — Busca de clientes sem respostas fora de ordem

Branch: `wp/415-customer-refresh-order`, base `main`.

## Entrega

Buscas e mudanças de filtros/página podem iniciar GETs concorrentes. Somente
a atualização mais recente pode aplicar lista, contagem, seleção, paginação,
aviso de falha, estado de carregamento ou notificação de sucesso. Respostas
anteriores são ignoradas, preservando o retry e os endpoints existentes.

## Validação

Handlers reais em DOM sintético com respostas controladas: sucesso e falha
na lista/contagem em ambas as ordens, preservação da seleção e do carregamento,
busca escapada, reset de página e recuperação por retry. Manter cobertura
existente de falhas isoladas e resultados vazios. Executar pytest, compileall,
diff-check, preflight e sintaxe JavaScript.

Sem schema, migrations, auth, dados reais, serviços externos ou escritas novas.
Um PR aberto ao supervisor; sem merge, deploy ou próxima WP nesta execução.
