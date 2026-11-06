# WP-423 — Histórico consistente com a oportunidade selecionada

Branch: `wp/423-opportunity-timeline-order`, base `main`.

## Problema e entrega

Respostas atrasadas do histórico podiam substituir ou apagar eventos de outra
oportunidade selecionada. Vincular a leitura à versão da seleção, ao ID e à
sessão; ignorar sucessos e falhas antigos e evitar iniciar uma leitura para
uma seleção já obsoleta. Limpar eventos anteriores assim que a seleção muda e ao iniciar a leitura atual.
Reabrir o mesmo ID usa uma nova versão. Preservar lista vazia e falha silenciosa
existentes, pois o histórico é informação complementar.

Sem alteração de API, schema, migrations, autorização ou ação externa.

## Validação

Teste Node via pytest executa o handler real com DOM e respostas sintéticos:
troca de seleção, fechamento, reabertura, troca de sessão, sucesso/falha antiga
antes/depois da atual, rota utilizada, vazio e falha atual. Testes existentes
cobrem o endpoint de histórico. Executar preflight e sintaxe JavaScript.
Entregar um único PR aberto ao supervisor, sem merge ou próximo WP.

## Evidência local

Preflight PASS: 3288 testes passaram, 2 warnings; compileall e diff-check
passaram. Sintaxe JavaScript e teste Node direcionado PASS. O teste falha
contra o código anterior da main. Somente respostas sintéticas e banco isolado
da suíte; nenhum serviço operacional utilizado.
