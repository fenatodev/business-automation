# WP-427 — Edição consistente com o customer selecionado

Branch: `wp/427-customer-edit-consistency`, base `main`.

## Problema e entrega

Uma resposta atrasada ao salvar a edição de um customer aplicava o retorno ao
detalhe atualmente aberto, mesmo quando o operador já havia trocado ou fechado
o customer. A sessão também poderia mudar antes da resposta. Capturar o ID,
versão da seleção e sessão no envio; aplicar a resposta, feedback e atualização
da lista somente se os três ainda corresponderem ao contexto atual. Impedir o
envio sem customer selecionado. A requisição já enviada não é cancelada.

Sem alteração de API, autenticação, tenant, schema, migration ou serviço
externo.

## Validação

Teste Node via pytest executa o listener real com respostas sintéticas:
troca de customer, reabertura do mesmo ID, fechamento, troca de sessão,
sucesso/falha atrasados e ausência de seleção. Executar `scripts/preflight.sh`,
`node --check app/operator_ui/app.js`, compileall e diff-check. Entregar um
único PR aberto para CI e supervisor; não fazer merge.
